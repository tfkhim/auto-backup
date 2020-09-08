from datetime import datetime

import pytest

from auto_backup import NotificationFormat


@pytest.fixture
def formatter():
    return NotificationFormat(add_timestamp=False)


@pytest.fixture
def task():
    return "test-task"


@pytest.fixture
def timestamp_formatter(monkeypatch):
    formatter = NotificationFormat(add_timestamp=True)

    def return_fixed_now():
        return datetime(2020, 11, 11, 11, 11)

    monkeypatch.setattr(formatter, "_get_current_time", return_fixed_now)

    return formatter


def test_format_task_failed_notification(formatter, task):
    assert formatter.task_failed(task) == "Task failed: test-task"


def test_format_timestamp_is_there_if_flag_is_true(timestamp_formatter):
    assert timestamp_formatter.message("alaaf") == "11.11.2020 11:11 - alaaf"
