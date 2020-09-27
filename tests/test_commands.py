from unittest.mock import MagicMock

import pytest

from auto_backup.tasks import RcloneCommand


@pytest.fixture
def run_subprocess():
    return MagicMock()


@pytest.fixture
def rclone(run_subprocess):
    return RcloneCommand(
        "/path/to/config", "my-source", "my-destination", run_subprocess
    )


@pytest.fixture
def subprocess_call(run_subprocess):
    class SublistExtract:
        def option_value(self, option_name):
            assert option_name in self.args
            index = self.args.index(option_name)
            return self.args[index + 1]

        @property
        def args(self):
            return run_subprocess.call_args[0][0]

    return SublistExtract()


def test_rclone_call(rclone, subprocess_call):
    rclone.execute()

    reference = (
        "rclone",
        "--verbose",
        "--config",
        "/path/to/config",
        "sync",
        "my-source",
        "my-destination",
    )
    assert subprocess_call.args == reference
