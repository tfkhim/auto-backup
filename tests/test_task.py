import pytest

from auto_backup.tasks import Task


@pytest.fixture
def tags():
    return ["tag1", "tag2"]


@pytest.fixture
def task(tags):
    return Task("task-name", tags, None, None)


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
