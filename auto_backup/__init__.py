#!/usr/bin/env python

import argparse

try:
    from functools import cached_property
except ImportError:
    from cached_property import cached_property

import toml

from auto_backup.config import (
    ConfigValueInjector,
    MergingTaskFactory,
    TaskConfigMerger,
    TaskFactory,
    TaskList,
)
from auto_backup.notifications import NotificationFormat, Notifications
from auto_backup.tasks import (
    BackupCommand,
    CheckBackupsCommand,
    PruneBackupsCommand,
    RcloneCommand,
    Task,
    TestFailTask,
)
from auto_backup.xmpp_notifications import XMPPnotifications


class ProgramSetup(object):
    COMMANDS = {
        "testfail": TestFailTask,
        "rclone": RcloneCommand,
        "backup": BackupCommand,
        "prune": PruneBackupsCommand,
        "check": CheckBackupsCommand,
    }

    NOTIFICATION_KEY = "XMPP"
    COMMAND_TYPE_KEY = "type"
    TASKS_KEY = "tasks"

    def __init__(self, config):
        self.config = config

    @cached_property
    def notify(self):
        formatter = NotificationFormat()
        return Notifications(self.notification_sender, formatter)

    @cached_property
    def notification_sender(self):
        injector = ConfigValueInjector(XMPPnotifications)
        return injector.build(self.config[self.NOTIFICATION_KEY])

    @cached_property
    def command_factory(self):
        factory = TaskFactory()
        for key, command_factory in self.COMMANDS.items():
            config_injector = self._create_value_injector(command_factory)
            factory.add_task_type(key, config_injector.build)
        return factory

    def _create_value_injector(self, factory):
        injector = ConfigValueInjector(factory)
        injector.provide_values(config=self.config, notify=self.notify)
        return injector

    @cached_property
    def task_factory(self):
        return MergingTaskFactory(
            self._task_factory_backend(), self._task_config_merger()
        )

    def _task_factory_backend(self):
        def task_from_config(task_config):
            command_type = task_config[self.COMMAND_TYPE_KEY]
            command = self.command_factory.create(command_type, task_config)
            injector = ConfigValueInjector(Task)
            injector.provide_values(command=command, notify=self.notify)
            return injector.build(task_config)

        return task_from_config

    def _task_config_merger(self):
        config_merger = TaskConfigMerger(self.config)

        def merge_task_config_with_section_from_config(task_config):
            section = task_config[self.COMMAND_TYPE_KEY]
            return config_merger.merge_with_task_config(section, task_config)

        return merge_task_config_with_section_from_config

    @cached_property
    def task_list(self):
        tasks = self.config.get(self.TASKS_KEY, [])
        return TaskList(self.task_factory.create, tasks)


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
    task_list = ProgramSetup(config).task_list

    execute_tasks(task_list, args.tags)


if __name__ == "__main__":
    main()
