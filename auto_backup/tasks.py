import datetime
import json
import os
import subprocess
import traceback

from dateutil.parser import isoparse

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


class BorgSubprocessEnvironment:
    def __init__(self, password, ssh_command):
        assign_arguments_to_self()

    def build(self):
        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = self.password

        if self.ssh_command:
            env["BORG_RSH"] = self.ssh_command

        return env


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
        self.subprocess_environment = BorgSubprocessEnvironment(
            repoConf["password"], ssh_command
        )

    def execute(self):
        args = self._build_backup_command_call()
        env = self.subprocess_environment.build()
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


class PruneBackupsCommand(object):
    def __init__(
        self,
        repository,
        config,
        within=None,
        daily=None,
        weekly=None,
        monthly=None,
        dry_run=False,
        ssh_command=None,
        run_subprocess=run_checked_subprocess,
    ):
        assign_arguments_to_self()

        repoConf = config["repositories"][self.repository]
        self.url = repoConf["url"]
        self.subprocess_environment = BorgSubprocessEnvironment(
            repoConf["password"], ssh_command
        )

    def execute(self):
        args = self._build_prune_command_call()
        env = self.subprocess_environment.build()
        self.run_subprocess(args, env=env)

    def _build_prune_command_call(self):
        prune_call = self._get_prune_call_base_arguments()
        self._append_dry_run_or_stats(prune_call)
        self._append_keep_options(prune_call)
        self._append_repository_url(prune_call)
        return tuple(prune_call)

    def _get_prune_call_base_arguments(self):
        return ["borg", "--verbose", "prune", "--list"]

    def _append_dry_run_or_stats(self, prune_call):
        prune_call.append("--dry-run" if self.dry_run else "--stats")

    def _append_keep_options(self, prune_call):
        for option_name in ("within", "daily", "weekly", "monthly"):
            option_value = getattr(self, option_name)
            if option_value is not None:
                prune_call.append(f"--keep-{option_name}")
                prune_call.append(str(option_value))

    def _append_repository_url(self, prune_call):
        prune_call.append(self.url)


class CheckBackupsCommand(object):
    def __init__(
        self,
        repositories,
        config,
        notify,
        ssh_command=None,
        run_subprocess=run_checked_subprocess,
    ):
        assign_arguments_to_self()

        self.repositories = [
            dict(name=name, **config["repositories"][name])
            for name in self.repositories
        ]

    def execute(self):
        lines = [
            self._get_message_line_for_repository(repo) for repo in self.repositories
        ]
        self.notify.message(self._format_final_message(lines))

    def _get_message_line_for_repository(self, repository):
        num_today, total = self._count_archives_for_repository(repository)
        return self._format_message_line(repository, num_today, total)

    def _count_archives_for_repository(self, repository):
        process_result = self._call_borg_list_for_repository(repository)
        parsed_output = json.loads(process_result.stdout)
        return self._sum_last_day_and_total(parsed_output)

    def _call_borg_list_for_repository(self, repository):
        args = self._build_list_command_call(repository["url"])
        env = self._build_subprocess_environment(repository["password"])
        return self.run_subprocess(args, env=env, capture_output=True)

    def _build_list_command_call(self, repository):
        return ("borg", "list", "--json", repository)

    def _build_subprocess_environment(self, password):
        return BorgSubprocessEnvironment(password, self.ssh_command).build()

    def _sum_last_day_and_total(self, borg_list_output):
        start_dates = self._get_archive_dates(borg_list_output)
        num_today = self._archives_within_24h(start_dates)
        return (num_today, len(start_dates))

    def _get_archive_dates(self, borg_list_output):
        start_dates_iso = map(lambda a: a["start"], borg_list_output["archives"])
        return list(map(isoparse, start_dates_iso))

    def _archives_within_24h(self, start_dates):
        now = datetime.datetime.now()
        one_day_delta = datetime.timedelta(days=1)
        return sum(map(lambda d: 1 if now - d < one_day_delta else 0, start_dates))

    def _format_message_line(self, repository, num_today, total):
        return f"{repository['name']}: {num_today} (24h) {total} (total)"

    def _format_final_message(self, lines):
        results = "\n".join(lines)
        return f"Backup check results:\n{results}"
