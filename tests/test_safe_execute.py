from unittest.mock import MagicMock

import pytest

from auto_backup import TaskBase


class TaskMock(TaskBase):
    def __init__(self, execute, notify):
        config = {
            "name": "TaskMock",
            "tags": [],
        }
        super().__init__(config, notify)

        self.execute = execute


@pytest.fixture
def succeeding_task():
    return TaskMock(lambda: None, None)


@pytest.fixture
def notify():
    return MagicMock()


@pytest.fixture
def failing_task(notify):
    def failing_execute():
        raise RuntimeError()

    return TaskMock(failing_execute, notify)


def test_success_returns_zero(succeeding_task):
    assert succeeding_task.safe_execute() == 0


def test_failure_returns_one(failing_task):
    assert failing_task.safe_execute() == 1


def test_failure_sends_exactly_one_notification(failing_task, notify):
    failing_task.safe_execute()

    assert notify.task_failed.call_count == 1
