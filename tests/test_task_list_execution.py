from unittest.mock import MagicMock, call

import pytest

from auto_backup import execute_tasks


@pytest.fixture
def empty_tags():
    return []


@pytest.fixture
def task_list():
    mock_list = [MagicMock(), MagicMock()]

    task_list = MagicMock()
    task_list.__iter__ = lambda self: iter(mock_list)
    task_list.filter_by_tags = MagicMock()

    return task_list


def get_execute_counts(mock_list):
    return [m.safe_execute.call_count for m in mock_list]


def test_executes_all_tasks(task_list, empty_tags):
    execute_tasks(task_list, empty_tags)

    assert get_execute_counts(task_list) == [1, 1]


def test_empty_tag_list_doesnt_call_filter(task_list, empty_tags):
    execute_tasks(task_list, empty_tags)

    assert task_list.filter_by_tags.call_count == 0


def test_calls_filter_if_tags_given(task_list):
    tags = ["tag"]

    execute_tasks(task_list, tags)

    assert task_list.filter_by_tags.call_args == call(tags)
