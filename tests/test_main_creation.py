from unittest.mock import MagicMock

import pytest

from auto_backup import (
    BackupTask,
    CheckBackups,
    PruneBackups,
    RcloneTask,
    create_notification,
    create_task_factory,
)


@pytest.fixture
def notify():
    return MagicMock


def config_type_pair(task_type, target_type):
    return (
        {
            "name": "test-task",
            "tags": [],
            "type": task_type,
        },
        target_type,
    )


def test_create_notification():
    config = {
        "XMPP": {
            "account": "test-sender",
            "password": "test-password",
            "recipient": "test-recipient",
        }
    }

    notify = create_notification(config)

    assert notify != None


@pytest.mark.parametrize(
    "task_config,target_type",
    [
        config_type_pair("rclone", RcloneTask),
        config_type_pair("backup", BackupTask),
        config_type_pair("prune", PruneBackups),
        config_type_pair("check", CheckBackups),
    ],
)
def test_create_task_factory_default_factories(notify, task_config, target_type):
    config = {
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

    factory = create_task_factory(config, notify)

    assert type(factory.create(task_config)) == target_type
