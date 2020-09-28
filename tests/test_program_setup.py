from unittest.mock import MagicMock

import pytest

from auto_backup import ProgramSetup
from auto_backup.tasks import (
    BackupCommand,
    CheckBackupsCommand,
    PruneBackupsCommand,
    RcloneCommand,
)


@pytest.fixture
def config():
    return {
        "XMPP": {
            "account": "test-sender",
            "password": "test-password",
            "recipient": "test-recipient",
        },
        "repositories": {"test": {"url": "test", "password": "test"}},
        "backup": {
            "repository": "test",
        },
        "prune": {
            "repository": "test",
        },
        "check": {
            "repositories": [],
        },
    }


@pytest.fixture
def task_config():
    return {
        "name": "test-task",
        "tags": [],
        "type": "test-type",
        "repository": "test",
        "repositories": [],
    }


@pytest.fixture
def task_list_config():
    return [
        {"name": "task1"},
        {"name": "task2"},
    ]


@pytest.fixture
def setup(config):
    return ProgramSetup(config)


@pytest.fixture
def task_factory_mock():
    factory = MagicMock()
    factory.create = MagicMock(wraps=lambda c: c["name"])
    return factory


@pytest.fixture
def command_factory_mock():
    return MagicMock()


def test_create_notification_sender(setup):
    sender = setup.notification_sender

    assert sender is not None


def test_create_notification(setup):
    setup.notification_sender = None

    notify = setup.notify

    assert notify is not None


@pytest.mark.parametrize(
    "command_type,target_type",
    [
        ("rclone", RcloneCommand),
        ("backup", BackupCommand),
        ("prune", PruneBackupsCommand),
        ("check", CheckBackupsCommand),
    ],
)
def test_default_command_factories(setup, task_config, command_type, target_type):
    setup.notify = None

    factory = setup.command_factory

    assert type(factory.create(command_type, task_config)) == target_type


def test_create_task_factory(setup, task_config, command_factory_mock):
    setup.notify = None
    setup.command_factory = command_factory_mock

    factory = setup.task_factory

    assert factory.create(task_config).name == "test-task"


def test_create_task_list_without_task_section(setup):
    task_list = setup.task_list

    assert list(task_list) == []


def test_create_task_list_from_task_section(
    setup, config, task_list_config, task_factory_mock
):
    config["tasks"] = task_list_config
    setup.task_factory = task_factory_mock

    task_list = setup.task_list

    assert list(task_list) == ["task1", "task2"]
