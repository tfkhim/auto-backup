from unittest.mock import MagicMock

import pytest

from auto_backup.tasks import BackupCommand, PruneBackupsCommand, RcloneCommand


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
def call_prune(config, run_subprocess):
    def call(**init_args):
        PruneBackupsCommand(
            "test-repo", config, run_subprocess=run_subprocess, **init_args
        ).execute()

    return call


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


def test_prune_call_base_command(call_prune, subprocess_call):
    call_prune()

    reference = (
        "borg",
        "--verbose",
        "prune",
        "--list",
        "--stats",
        "my-url",
    )
    assert subprocess_call.args == reference


def test_prune_call_sets_password(call_prune, subprocess_call):
    call_prune()

    assert subprocess_call.env["BORG_PASSPHRASE"] == "my-password"


def test_prune_call_with_ssh_command(call_prune, subprocess_call):
    call_prune(ssh_command="my-ssh")

    assert subprocess_call.env["BORG_RSH"] == "my-ssh"


def test_prune_call_dry_run_command(call_prune, subprocess_call):
    call_prune(dry_run=True)

    reference = (
        "borg",
        "--verbose",
        "prune",
        "--list",
        "--dry-run",
        "my-url",
    )
    assert subprocess_call.args == reference


def prune_cmd_reference(*keep_options):
    return ("borg", "--verbose", "prune", "--list", "--stats", *keep_options, "my-url")


@pytest.mark.parametrize(
    "extra_args,reference",
    [
        (
            {"monthly": "my-monthly"},
            prune_cmd_reference("--keep-monthly", "my-monthly"),
        ),
        (
            {"within": "my-within", "daily": "my-daily"},
            prune_cmd_reference(
                "--keep-within", "my-within", "--keep-daily", "my-daily"
            ),
        ),
        (
            {"within": "my-within", "weekly": "my-weekly"},
            prune_cmd_reference(
                "--keep-within", "my-within", "--keep-weekly", "my-weekly"
            ),
        ),
        (
            {"within": "my-within", "daily": "my-daily", "monthly": "my-monthly"},
            prune_cmd_reference(
                "--keep-within",
                "my-within",
                "--keep-daily",
                "my-daily",
                "--keep-monthly",
                "my-monthly",
            ),
        ),
        (
            {
                "within": "my-within",
                "daily": "my-daily",
                "weekly": "my-weekly",
                "monthly": "my-monthly",
            },
            prune_cmd_reference(
                "--keep-within",
                "my-within",
                "--keep-daily",
                "my-daily",
                "--keep-weekly",
                "my-weekly",
                "--keep-monthly",
                "my-monthly",
            ),
        ),
    ],
)
def test_prune_with_different_keep_option_values(
    call_prune, subprocess_call, extra_args, reference
):
    call_prune(**extra_args)

    assert subprocess_call.args == reference
