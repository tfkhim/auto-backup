#!/usr/bin/env python

import argparse
import datetime

import toml

from auto_backup.config import (
    MergingTaskFactory,
    TaskConfigMerger,
    TaskFactory,
    TaskList,
)
from auto_backup.notifications import NotificationFormat, Notifications
from auto_backup.tasks import (
    BackupTask,
    CheckBackups,
    PruneBackups,
    RcloneTask,
    TestFailTask,
)
from auto_backup.xmpp_notifications import XMPPnotifications


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
