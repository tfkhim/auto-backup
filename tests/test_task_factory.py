from unittest.mock import MagicMock, call

import pytest

from auto_backup import TaskFactory


@pytest.fixture
def config():
    return {"test-key": "test-value"}


@pytest.fixture
def notify():
    return MagicMock()


@pytest.fixture
def factory(config, notify):
    return TaskFactory(config, notify)


@pytest.fixture
def type_factory():
    return MagicMock(return_value="task-created")


@pytest.fixture
def another_type_factory():
    return MagicMock(return_value="another-task-created")


@pytest.fixture
def task_config():
    return {"task-key": "task-value"}


def test_can_create_added_type(factory, type_factory, task_config):
    factory.add_task_type("test-type", type_factory)

    assert factory.create("test-type", task_config) == "task-created"


def test_add_multiple_types(factory, type_factory, another_type_factory, task_config):
    factory.add_task_types(
        (("test-type", type_factory), ("another-type", another_type_factory))
    )

    assert factory.create("test-type", task_config) == "task-created"
    assert factory.create("another-type", task_config) == "another-task-created"


def test_config_passed_to_type_factory(
    factory, type_factory, task_config, config, notify
):
    factory.add_task_type("test-type", type_factory)

    factory.create("test-type", task_config)

    type_factory.call_args == call(task_config, notify, config)
