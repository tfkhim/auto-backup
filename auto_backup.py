#!/usr/bin/env python

import argparse
import asyncio
import copy
import datetime
import itertools
import json
import os
import subprocess
import sys
import traceback

import aioxmpp
import toml


class TaskBase(object):
    def __init__(self, taskConfig, notify, *args, **kwargs):
        self.name = taskConfig.pop("name")
        self.tags = set(taskConfig.pop("tags"))
        self.notify = notify

        for key, value in taskConfig.items():
            setattr(self, key, value)

    def __str__(self):
        return self.name

    def isActive(self, activeTags):
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

    def merge_with_task_config(self, task_type, task_config):
        task_type_config = self._get_task_type_config(task_type)

        merged_config = dict()
        merged_config.update(task_type_config)
        merged_config.update(task_config)
        return merged_config

    def _get_task_type_config(self, task_type):
        return self.config.get(task_type, {})


class MergingTaskFactory(object):
    def __init__(self, factory, merger):
        self.task_factory = factory
        self.merger = merger

    def create(self, task_config):
        task_type = self._get_task_type(task_config)
        merged_config = self._merge_task_and_type_config(task_config)
        return self.task_factory.create(task_type, merged_config)

    def _get_task_type(self, task_config):
        return task_config["type"]

    def _merge_task_and_type_config(self, task_config):
        task_type = self._get_task_type(task_config)
        return self.merger.merge_with_task_config(task_type, task_config)


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


class Notifications(object):
    def __init__(self, sender, formatter):
        self.notification_sender = sender
        self.formatter = formatter

    def task_failed(self, task):
        self.notification_sender.send(self.formatter.task_failed(task))

    def message(self, message):
        self.notification_sender.send(self.formatter.message(message))


class XMPPnotifications(object):
    def __init__(self, account, password, recipient):
        self.sender = account
        self.password = password
        self.recipient = recipient

    def send(self, message):
        asyncio.run(self._async_send(message))

    async def _async_send(self, message):
        client = self._setup_client()
        message = self._prepare_message(message)
        await self._connect_and_send(client, message)

    def _setup_client(self):
        jid = aioxmpp.JID.fromstr(self.sender)
        sec_layer = aioxmpp.make_security_layer(self.password)

        return aioxmpp.PresenceManagedClient(jid, sec_layer)

    def _prepare_message(self, message):
        recipient_jid = aioxmpp.JID.fromstr(self.recipient)
        xmpp_msg = aioxmpp.Message(to=recipient_jid, type_=aioxmpp.MessageType.CHAT)
        xmpp_msg.body[None] = message
        return xmpp_msg

    async def _connect_and_send(self, client, message):
        async with client.connected() as stream:
            await stream.send(message)


class NotificationFormat(object):
    def __init__(self, add_timestamp=True):
        self.add_timestamp = add_timestamp

    def task_failed(self, task):
        return self.message(self._get_task_failed_string(task))

    def message(self, message):
        if self.add_timestamp:
            now = self._get_current_time()
            message = self._prepend_timestamp_to_message(now, message)
        return message

    def _get_task_failed_string(self, task):
        return "Task failed: {}".format(task)

    def _get_current_time(self):
        return datetime.datetime.now()

    def _prepend_timestamp_to_message(self, time, message):
        return "{:%d.%m.%Y %H:%M} - {}".format(time, message)


def create_notification(config):
    sender = XMPPnotifications(**config["XMPP"])
    formatter = NotificationFormat()
    return Notifications(sender, formatter)


def create_config_merger(config):
    return TaskConfigMerger(config)


def create_task_factory(config, notify):
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


def main():
    parser = argparse.ArgumentParser(description="Execute backup tasks")
    parser.add_argument("--tag", dest="tags", action="append")
    parser.add_argument("config", nargs=1)

    args = parser.parse_args()

    config = toml.load(args.config)
    notify = create_notification(config)
    merger = create_config_merger(config)
    task_factory = create_task_factory(config, notify)
    task_factory = MergingTaskFactory(task_factory, merger)

    tasks = list(map(task_factory.create, config.get("tasks", [])))

    if args.tags:
        tasks = [t for t in tasks if t.isActive(args.tags)]

    for task in tasks:
        task.safe_execute()


if __name__ == "__main__":
    main()
