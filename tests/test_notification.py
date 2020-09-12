from unittest.mock import MagicMock, Mock, call

import pytest

from auto_backup.notifications import Notifications


@pytest.fixture
def formatter():
    formatter = MagicMock()
    formatter.task_failed = Mock(return_value="task-failed-message")
    formatter.message = Mock(return_value="normal-message")
    return formatter


@pytest.fixture
def sender():
    return MagicMock()


@pytest.fixture
def notify(sender, formatter):
    return Notifications(sender, formatter)


def test_failed_task_notification_is_formatted_and_sent(notify, sender):
    notify.task_failed("test")

    assert sender.send.call_args == call("task-failed-message")


def test_message_notification_is_formatted_and_sent(notify, sender):
    notify.message("test")

    assert sender.send.call_args == call("normal-message")
