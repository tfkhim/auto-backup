import datetime
import json
import os
import subprocess
import traceback

from auto_backup.argument_assigner import assign_arguments_to_self


class Task(object):
    def __init__(self, name, tags, command, notify):
        self.name = name
        self.tags = set(tags)
        self.command = command
        self.notify = notify

    def __str__(self):
        return self.name

    def is_active(self, activeTags):
        return not self.tags.isdisjoint(activeTags)

    def safe_execute(self):
        try:
            self.command.execute()
            return 0
        except Exception:
            traceback.print_exc()
            self.notify.task_failed(self)
            return 1


def run_checked_subprocess(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


class TestFailTask(object):
    def execute(self):
        raise RuntimeError("Task failed")


class RcloneCommand(object):
    def __init__(
        self, config_file, source, destination, run_subprocess=run_checked_subprocess
    ):
        assign_arguments_to_self()

    def execute(self):
        args = (
            "rclone",
            "--verbose",
            "--config",
            self.config_file,
            "sync",
            self.source,
            self.destination,
        )

        self.run_subprocess(args)


class BackupCommand(object):
    def __init__(
        self,
        source,
        repository,
        config,
        excludes=[],
        ssh_command=None,
        run_subprocess=run_checked_subprocess,
    ):
        assign_arguments_to_self()

        repoConf = config["repositories"][self.repository]
        self.url = repoConf["url"]
        self.password = repoConf["password"]

    def execute(self):
        args = self._build_backup_command_call()
        env = self._build_subprocess_environment()
        self.run_subprocess(args, cwd=self.source, env=env)

    def _build_backup_command_call(self):
        backup_call = self._get_backup_call_base_arguments()
        self._append_exclude_options(backup_call)
        self._append_archive(backup_call)
        self._append_directory(backup_call)
        return tuple(backup_call)

    def _get_backup_call_base_arguments(self):
        return ["borg", "--verbose", "create"]

    def _append_exclude_options(self, backup_call):
        for exclude in self.excludes:
            backup_call.append("--exclude")
            backup_call.append(exclude)

    def _append_archive(self, backup_call):
        backup_call.append(f"{self.url}::{{hostname}}-{{now}}")

    def _append_directory(self, backup_call):
        backup_call.append(".")

    def _build_subprocess_environment(self):
        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = self.password

        if self.ssh_command:
            env["BORG_RSH"] = self.ssh_command

        return env


class PruneBackups(object):
    def __init__(
        self, repository, dryRun, within, daily, weekly, monthly, sshCommand, config
    ):
        assign_arguments_to_self()

        repoConf = config["repositories"][self.repository]
        self.url = repoConf["url"]
        self.password = repoConf["password"]

    def execute(self):
        args = ["borg", "--verbose", "prune", "--list"]

        if self.dryRun:
            args.append("--dry-run")
        else:
            args.append("--stats")

        for flag in ("within", "daily", "weekly", "monthly"):
            if getattr(self, flag):
                args.append(f"--keep-{flag}")
                args.append(str(getattr(self, flag)))

        args.append(self.url)

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = self.password

        if self.sshCommand:
            env["BORG_RSH"] = self.sshCommand

        subprocess.run(args, env=env, check=True)


class CheckBackups(object):
    def __init__(self, repositories, sshCommand, notify, config):
        assign_arguments_to_self()

        self.repositories = [
            dict(name=name, **config["repositories"][name])
            for name in self.repositories
        ]

    def countOne(self, repository, password):
        args = ("borg", "list", "--json", repository)

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = password

        if self.sshCommand:
            env["BORG_RSH"] = self.sshCommand

        result = subprocess.run(args, env=env, check=True, capture_output=True)

        startDates = map(lambda a: a["start"], json.loads(result.stdout)["archives"])
        startDates = list(map(datetime.datetime.fromisoformat, startDates))

        now = datetime.datetime.now()
        oneDay = datetime.timedelta(days=1)
        numOneDay = sum(map(lambda d: 1 if now - d < oneDay else 0, startDates))

        return (numOneDay, len(startDates))

    def execute(self):
        def formatLine(repo):
            numToday, total = self.countOne(repo["url"], repo["password"])
            return f"{repo['name']}: {numToday} (24h) {total} (total)"

        lines = [formatLine(repo) for repo in self.repositories]

        results = "\n".join(lines)
        self.notify.message(f"Backup check results:\n{results}")
