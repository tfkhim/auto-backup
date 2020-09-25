import datetime
import itertools
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


class TestFailTask(object):
    def execute(self):
        raise RuntimeError("Task failed")


class RcloneTask(object):
    def __init__(self, configFile, source, destination):
        assign_arguments_to_self()

    def execute(self):
        args = (
            "rclone",
            "--verbose",
            "--config",
            self.configFile,
            "sync",
            self.source,
            self.destination,
        )

        subprocess.run(args, check=True)


class BackupTask(object):
    def __init__(self, source, repository, excludes, sshCommand, config):
        assign_arguments_to_self()

        repoConf = config["repositories"][self.repository]
        self.url = repoConf["url"]
        self.password = repoConf["password"]

    def execute(self):
        archive = "{}::{{hostname}}-{{now}}".format(self.url)

        excludes = zip(itertools.repeat("--exclude"), self.excludes)
        excludes = itertools.chain.from_iterable(excludes)

        args = ("borg", "--verbose", "create", *excludes, archive, ".")

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = self.password

        if self.sshCommand:
            env["BORG_RSH"] = self.sshCommand

        subprocess.run(args, cwd=self.source, env=env, check=True)


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
                args.append("--keep-{}".format(flag))
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
            return "{}: {} (24h) {} (total)".format(repo["name"], numToday, total)

        lines = [formatLine(repo) for repo in self.repositories]

        self.notify.message("Backup check results:\n{} ".format("\n".join(lines)))
