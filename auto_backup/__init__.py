#!/usr/bin/env python

import argparse
import copy
import datetime
import itertools
import json
import os
import subprocess
import sys
import traceback

import toml

from auto_backup.notifications import NotificationFormat, Notifications
from auto_backup.xmpp_notifications import XMPPnotifications


class TaskBase(object):
    def __init__(self, taskConfig, notify, *args, **kwargs):
        self.name = taskConfig.pop("name")
        self.tags = set(taskConfig.pop("tags"))
        self.notify = notify

        for key, value in taskConfig.items():
            setattr(self, key, value)

    def __str__(self):
        return self.name

    def is_active(self, activeTags):
        return not self.tags.isdisjoint(activeTags)

    def safe_execute(self):
        try:
            self.execute()
            return 0
        except:
            traceback.print_exc()
            self.notify.task_failed(self)
            return 1


class TestFailTask(TaskBase):
    def execute(self):
        raise RuntimeError("Task failed")


class RcloneTask(TaskBase):
    def execute(self):
        args = (
            "rclone",
            "--verbose",
            "--config",
            self.configFile,
            "sync",
            self.source,
            self.destination,
        )

        subprocess.run(args, check=True)


class BackupTask(TaskBase):
    def __init__(self, taskConfig, notify, config):
        super().__init__(taskConfig, notify)

        repoConf = config["repositories"][self.repository]
        self.url = repoConf["url"]
        self.password = repoConf["password"]

    def execute(self):
        archive = "{}::{{hostname}}-{{now}}".format(self.url)

        excludes = zip(itertools.repeat("--exclude"), self.excludes)
        excludes = itertools.chain.from_iterable(excludes)

        args = ("borg", "--verbose", "create", *excludes, archive, ".")

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = self.password

        if hasattr(self, "sshCommand"):
            env["BORG_RSH"] = self.sshCommand

        subprocess.run(args, cwd=self.source, env=env, check=True)


class PruneBackups(TaskBase):
    def __init__(self, taskConfig, notify, config):
        super().__init__(taskConfig, notify)

        repoConf = config["repositories"][self.repository]
        self.url = repoConf["url"]
        self.password = repoConf["password"]

    def execute(self):
        args = ["borg", "--verbose", "prune", "--list"]

        if getattr(self, "dryRun", False):
            args.append("--dry-run")
        else:
            args.append("--stats")

        for flag in ("within", "daily", "weekly", "monthly"):
            if hasattr(self, flag):
                args.append("--keep-{}".format(flag))
                args.append(str(getattr(self, flag)))

        args.append(self.url)

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = self.password

        if hasattr(self, "sshCommand"):
            env["BORG_RSH"] = self.sshCommand

        subprocess.run(args, env=env, check=True)


class CheckBackups(TaskBase):
    def __init__(self, taskConfig, notify, config):
        super().__init__(taskConfig, notify)

        self.repositories = [
            dict(name=name, **config["repositories"][name])
            for name in self.repositories
        ]

    def countOne(self, repository, password):
        args = ("borg", "list", "--json", repository)

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = password

        if hasattr(self, "sshCommand"):
            env["BORG_RSH"] = self.sshCommand

        result = subprocess.run(args, env=env, check=True, capture_output=True)

        startDates = map(lambda a: a["start"], json.loads(result.stdout)["archives"])
        startDates = list(map(datetime.datetime.fromisoformat, startDates))

        now = datetime.datetime.now()
        oneDay = datetime.timedelta(days=1)
        numOneDay = sum(map(lambda d: 1 if now - d < oneDay else 0, startDates))

        return (numOneDay, len(startDates))

    def execute(self):
        def formatLine(repo):
            numToday, total = self.countOne(repo["url"], repo["password"])
            return "{}: {} (24h) {} (total)".format(repo["name"], numToday, total)

        lines = [formatLine(repo) for repo in self.repositories]

        self.notify.message("Backup check results:\n{} ".format("\n".join(lines)))


class TaskConfigMerger(object):
    def __init__(self, config):
        self.config = config

    def merge_with_task_config(self, config_section, task_config):
        config_section = self._get_config_section(config_section)

        merged_config = dict()
        merged_config.update(config_section)
        merged_config.update(task_config)
        return merged_config

    def _get_config_section(self, section):
        return self.config.get(section, {})


class MergingTaskFactory(object):
    def __init__(self, factory, merger):
        self.task_factory = factory
        self.merger = merger

    def create(self, task_config):
        merged_config = self._merge_task_and_type_config(task_config)
        return self.task_factory(merged_config)

    def _merge_task_and_type_config(self, task_config):
        return self.merger(task_config)


class TaskFactory(object):
    def __init__(self, config, notify):
        self.factories = dict()
        self.config = config
        self.notify = notify

    def add_task_type(self, type_key, factory):
        self.factories[type_key] = factory

    def add_task_types(self, key_factory_pairs):
        for type_key, factory in key_factory_pairs:
            self.add_task_type(type_key, factory)

    def create(self, type_key, task_config):
        return self.factories[type_key](task_config, self.notify, self.config)


class TaskList(object):
    def __init__(self, task_factory, config):
        self.task_factory = task_factory
        self.config = config
        self.filter_func = lambda t: t

    def __iter__(self):
        created_tasks = map(self.task_factory, self.config)
        return filter(self.filter_func, created_tasks)

    def filter_by_tags(self, tags):
        self.filter_func = lambda t: t.is_active(tags)


def create_notification(config):
    sender = XMPPnotifications(**config["XMPP"])
    formatter = NotificationFormat()
    return Notifications(sender, formatter)


def create_task_factory(config, notify):
    internal_task_factory = create_internal_task_factory(config, notify)
    merger = TaskConfigMerger(config)
    return create_config_aware_mergin_factory(merger, internal_task_factory)


def create_internal_task_factory(config, notify):
    factory = TaskFactory(config, notify)

    default_factories = {
        "testfail": TestFailTask,
        "rclone": RcloneTask,
        "backup": BackupTask,
        "prune": PruneBackups,
        "check": CheckBackups,
    }
    factory.add_task_types(default_factories.items())

    return factory


def create_config_aware_mergin_factory(merger, task_factory):
    merge_and_task_type_key = "type"

    def task_from_type_factory(config):
        return task_factory.create(config[merge_and_task_type_key], config)

    def merge_using_config_key(config):
        return merger.merge_with_task_config(config[merge_and_task_type_key], config)

    return MergingTaskFactory(task_from_type_factory, merge_using_config_key)


def create_task_list(factory, config):
    return TaskList(factory.create, config.get("tasks", []))


def execute_tasks(task_list, tags):
    if tags:
        task_list.filter_by_tags(tags)

    for task in task_list:
        task.safe_execute()


def main():
    parser = argparse.ArgumentParser(description="Execute backup tasks")
    parser.add_argument("--tag", dest="tags", action="append")
    parser.add_argument("config", nargs=1)

    args = parser.parse_args()

    config = toml.load(args.config)
    notify = create_notification(config)
    factory = create_task_factory(config, notify)
    task_list = create_task_list(factory, config)

    execute_tasks(task_list, args.tags)


if __name__ == "__main__":
    main()
