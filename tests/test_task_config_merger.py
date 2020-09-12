import pytest

from auto_backup.config import TaskConfigMerger


@pytest.fixture
def config():
    return {
        "test-task": {
            "test-key-1": "type-value-1",
            "test-key-2": "type-value-2",
        }
    }


@pytest.fixture
def merger(config):
    return TaskConfigMerger(config)


@pytest.fixture
def task_config():
    return {
        "test-key-1": "task-value-1",
    }


def test_task_config_overrides_type_default(merger, task_config):
    config = merger.merge_with_task_config("test-task", task_config)

    assert config["test-key-1"] == "task-value-1"


def test_uses_type_default_when_no_task_override(merger, task_config):
    config = merger.merge_with_task_config("test-task", task_config)

    assert config["test-key-2"] == "type-value-2"


def test_no_type_section_results_in_task_config_only(merger, task_config):
    config = merger.merge_with_task_config("no-section-type", task_config)

    assert config == task_config


def test_key_in_task_config_but_not_in_section(merger, task_config):
    task_config["task-key-3"] = "task-value-3"

    config = merger.merge_with_task_config("test-task", task_config)

    assert config["task-key-3"] == "task-value-3"
