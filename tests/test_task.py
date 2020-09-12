import pytest

from auto_backup.tasks import TaskBase


@pytest.fixture
def config():
    return {
        "name": "task-name",
        "tags": ["tag1", "tag2"],
    }


@pytest.fixture
def task(config):
    return TaskBase(config, None)


def create_task(config):
    return TaskBase(config, None)


def test_task_expects_name_config(config):
    del config["name"]

    with pytest.raises(KeyError):
        create_task(config)


def test_task_expects_tags_config(config):
    del config["tags"]

    with pytest.raises(KeyError):
        create_task(config)


def test_task_add_configuration_as_members(config):
    config["test_key"] = "test_value"

    task = create_task(config)

    assert task.test_key == "test_value"


def test_task_to_string_is_name(task):
    assert str(task) == "task-name"


def test_task_is_active_with_single_tag(task):
    assert task.is_active(["tag1"])


def test_task_is_active_list_with_one_matching_tag(task):
    assert task.is_active(["tag2", "tag3"])


def test_task_is_inactive_empty_input_list(task):
    assert not task.is_active([])


def test_task_is_inactive_list_with_not_matching_tags(task):
    assert not task.is_active(["tag3"])
