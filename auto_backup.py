#!/usr/bin/env python

import os
import sys
import toml
import copy
import json
import asyncio
import aioxmpp
import argparse
import datetime
import itertools
import traceback
import subprocess

class TaskBase(object):
    def __init__(self, taskConfig, notify, *args, **kwargs):
        self.name = taskConfig.pop("name")
        self.tags = set(taskConfig.pop("tags"))
        self.notify = notify

        for key, value in taskConfig.items():
            setattr(self, key, value)

    def __str__(self):
        return self.name

    def isActive(self, activeTags):
        return not self.tags.isdisjoint(activeTags)

    def safe_execute(self):
        try:
            self.execute()
            return 0
        except:
            traceback.print_exc()
            self.notify.send("Task failed: {}".format(self))
            return 1

class TestFailTask(TaskBase):
    def execute(self):
        raise RuntimeError("Task failed")

class RcloneTask(TaskBase):
    def execute(self):
        args = (
            "rclone",
            "--verbose",
            "--config", self.configFile,
            "sync",
            self.source,
            self.destination
        )

        subprocess.run(args, check=True)

class BackupTask(TaskBase):
    def __init__(self, taskConfig, notify, config):
        super().__init__(taskConfig, notify)

        repoConf = config["repositories"][self.repository]
        self.url = repoConf["url"]
        self.password = repoConf["password"]

    def execute(self):
        archive = "{}::{{hostname}}-{{now}}".format(self.url)

        excludes = zip(itertools.repeat("--exclude"), self.excludes)
        excludes = itertools.chain.from_iterable(excludes)

        args = (
            "borg",
            "--verbose",
            "create",
            *excludes,
            archive,
            "."
        )

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = self.password

        if hasattr(self, "sshCommand"):
            env["BORG_RSH"] = self.sshCommand

        subprocess.run(args, cwd=self.source, env=env, check=True)

class PruneBackups(TaskBase):
    def __init__(self, taskConfig, notify, config):
        super().__init__(taskConfig, notify)

        repoConf = config["repositories"][self.repository]
        self.url = repoConf["url"]
        self.password = repoConf["password"]

    def execute(self):
        args = [
            "borg",
            "--verbose",
            "prune",
            "--list"
        ]

        if getattr(self, "dryRun", False):
            args.append("--dry-run")
        else:
            args.append("--stats")

        for flag in ("within", "daily", "weekly", "monthly"):
            if hasattr(self, flag):
                args.append("--keep-{}".format(flag))
                args.append(str(getattr(self, flag)))

        args.append(self.url)

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = self.password

        if hasattr(self, "sshCommand"):
            env["BORG_RSH"] = self.sshCommand

        subprocess.run(args, env=env, check=True)

class CheckBackups(TaskBase):
    def __init__(self, taskConfig, notify, config):
        super().__init__(taskConfig, notify)

        self.repositories = [dict(name=name, **config["repositories"][name]) for name in self.repositories]

    def countOne(self, repository, password):
        args = (
            "borg",
            "list",
            "--json",
            repository
        )

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = password

        if hasattr(self, "sshCommand"):
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

        self.notify.send("Backup check results:\n{} ".format("\n".join(lines)))

class Config(object):
    TASK_FACTORIES={
        "testfail" : TestFailTask,
        "rclone"   : RcloneTask,
        "backup"   : BackupTask,
        "prune"    : PruneBackups,
        "check"    : CheckBackups
    }

    def __init__(self, tomlFile):
        self._config = toml.load(tomlFile)
        self._tasks = self._config.pop("tasks", [])
        self._notify = None

    @property
    def notify(self):
        if not self._notify:
            self._notify = Notifications(**self._config["XMPP"])
        return self._notify

    @property
    def tasks(self):
        def make_task(taskConf):
            tType = taskConf["type"]
            fullTaskConf = copy.copy(self._config.get(tType, {}))
            fullTaskConf.update(taskConf)
            return Config.TASK_FACTORIES[tType](fullTaskConf, self.notify, self._config)

        return list(map(make_task, self._tasks))

class Notifications(object):
    def __init__(self, account, password, recipient):
        self.sender = account
        self.password = password
        self.recipient = recipient

    async def __sendImpl(self, message):
        jid = jid = aioxmpp.JID.fromstr(self.sender)
        sec_layer = aioxmpp.make_security_layer(self.password)
        recipient_jid = aioxmpp.JID.fromstr(self.recipient)

        client = aioxmpp.PresenceManagedClient(jid, sec_layer)

        async with client.connected() as stream:
            xmppMsg = aioxmpp.Message(to=recipient_jid, type_=aioxmpp.MessageType.CHAT)

            xmppMsg.body[None] = message

            await client.send(xmppMsg)

    def send(self, message, with_time=True):
        if with_time:
            now = datetime.datetime.now()
            timestamp = now.strftime("")
            message = "{:%d.%m.%Y %H:%M} - {}".format(now, message)
        asyncio.run(self.__sendImpl(message))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute backup tasks")
    parser.add_argument("--tag", dest="tags", action="append")
    parser.add_argument("config", nargs=1)

    args = parser.parse_args()

    config = Config(args.config)

    tasks = config.tasks

    if args.tags:
        tasks = [t for t in tasks if t.isActive(args.tags)]

    for task in tasks:
        task.safe_execute()
