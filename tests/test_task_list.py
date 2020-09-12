from unittest.mock import MagicMock, call

import pytest

from auto_backup.config import TaskList


class MockTask(str):
    def is_active(self, tags):
        return self in tags


@pytest.fixture
def task_factory():
    def mock_factory(config):
        return MockTask(config["name"])

    return MagicMock(wraps=mock_factory)


@pytest.fixture
def config():
    return [{"name": "task-1"}, {"name": "task-2"}]


@pytest.fixture
def task_list(task_factory, config):
    return TaskList(task_factory, config)


def test_creates_tasks_from_configuration(task_list):
    assert list(task_list) == ["task-1", "task-2"]


def test_factory_called_twice_with_task_config(task_list, task_factory, config):
    list(task_list)

    assert task_factory.call_args_list == [call(config[0]), call(config[1])]


def test_filter_by_tags(task_list):
    task_list.filter_by_tags(["task-1"])

    assert list(task_list) == ["task-1"]
