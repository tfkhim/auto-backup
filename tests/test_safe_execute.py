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
def execute_succeeds():
    return TaskMock(lambda: None, None)

def test_success_returns_zero(execute_succeeds):
    assert execute_succeeds.safe_execute() == 0

