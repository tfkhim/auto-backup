from unittest.mock import MagicMock

import pytest

from auto_backup.tasks import BackupCommand, RcloneCommand


@pytest.fixture
def run_subprocess():
    return MagicMock()


@pytest.fixture
def rclone(run_subprocess):
    return RcloneCommand(
        "/path/to/config", "my-source", "my-destination", run_subprocess=run_subprocess
    )


@pytest.fixture
def config():
    return {"repositories": {"test-repo": {"url": "my-url", "password": "my-password"}}}


@pytest.fixture
def backup(config, run_subprocess):
    return BackupCommand(
        "/my/source/dir", "test-repo", config, run_subprocess=run_subprocess
    )


@pytest.fixture
def backup_with_ssh_and_excludes(config, run_subprocess):
    excludes = [".my-exclude", ".my-other-exclude"]
    return BackupCommand(
        "/my/source/dir",
        "test-repo",
        config,
        excludes=excludes,
        ssh_command="my-ssh",
        run_subprocess=run_subprocess,
    )


@pytest.fixture
def subprocess_call(run_subprocess):
    class SublistExtract:
        @property
        def args(self):
            return run_subprocess.call_args[0][0]

        @property
        def cwd(self):
            return self._get_kwarg("cwd")

        @property
        def env(self):
            return self._get_kwarg("env")

        def _get_kwarg(self, key):
            return run_subprocess.call_args[1].get(key)

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


def test_backup_call_without_excludes(backup, subprocess_call):
    backup.execute()

    reference = ("borg", "--verbose", "create", "my-url::{hostname}-{now}", ".")
    assert subprocess_call.args == reference


def test_backup_call_executed_in_source_directory(backup, subprocess_call):
    backup.execute()

    assert subprocess_call.cwd == "/my/source/dir"


def test_backup_call_sets_password(backup, subprocess_call):
    backup.execute()

    assert subprocess_call.env["BORG_PASSPHRASE"] == "my-password"


def test_backup_call_with_excludes(backup_with_ssh_and_excludes, subprocess_call):
    backup_with_ssh_and_excludes.execute()

    reference = (
        "borg",
        "--verbose",
        "create",
        "--exclude",
        ".my-exclude",
        "--exclude",
        ".my-other-exclude",
        "my-url::{hostname}-{now}",
        ".",
    )
    assert subprocess_call.args == reference


def test_backup_call_with_ssh_command(backup_with_ssh_and_excludes, subprocess_call):
    backup_with_ssh_and_excludes.execute()

    assert subprocess_call.env["BORG_RSH"] == "my-ssh"
