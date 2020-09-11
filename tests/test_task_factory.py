from unittest.mock import MagicMock, call

import pytest

from auto_backup import MergingTaskFactory, TaskFactory


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


@pytest.fixture
def factory_mock():
    factory = MagicMock()
    factory.create = MagicMock(return_value="task-from-mock-factory")
    return factory


@pytest.fixture
def merging():
    merging = MagicMock()
    merging.merge_with_task_config = MagicMock(return_value="merged-config")
    return merging


@pytest.fixture
def merging_factory(merging, factory_mock):
    return MergingTaskFactory(factory_mock, merging)


@pytest.fixture
def task_config_with_type():
    return {"type": "test-type"}


def test_merging_factory_returns_task_from_task_factory(
    merging_factory, task_config_with_type
):
    task = merging_factory.create(task_config_with_type)

    assert task == "task-from-mock-factory"


def test_task_gets_created_from_merged_config(
    merging_factory, task_config_with_type, factory_mock
):
    merging_factory.create(task_config_with_type)

    assert factory_mock.create.call_args == call("test-type", "merged-config")
