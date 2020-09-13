from unittest.mock import MagicMock

import pytest

from auto_backup.tasks import Task


@pytest.fixture
def succeeding_command():
    mock = MagicMock()
    mock.execute = lambda: None
    return mock


@pytest.fixture
def failing_command(succeeding_command):
    def failing_execute():
        raise RuntimeError()

    mock = MagicMock()
    mock.execute = failing_execute
    return mock


@pytest.fixture
def notify():
    return MagicMock()


@pytest.fixture
def succeeding_task(succeeding_command, notify):
    return Task("succeeding", [], succeeding_command, notify)


@pytest.fixture
def failing_task(failing_command, notify):
    return Task("failing", [], failing_command, notify)


def test_success_returns_zero(succeeding_task):
    assert succeeding_task.safe_execute() == 0


def test_failure_returns_one(failing_task):
    assert failing_task.safe_execute() == 1


def test_failure_sends_exactly_one_notification(failing_task, notify):
    failing_task.safe_execute()

    assert notify.task_failed.call_count == 1
