#!/usr/bin/env python

import os
import sys
import toml
import copy
import json
import asyncio
import aioxmpp
import datetime
import itertools
import traceback
import subprocess

class TaskBase(object):
    def __init__(self, *, name, notify, **kwargs):
        self.name = name
        self.notify = notify

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return self.name

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
    def execute(self):
        archive = "{}::{{hostname}}-{{now}}".format(self.repository)

        excludes = zip(itertools.repeat("--exclude"), self.excludes)
        excludes = itertools.chain.from_iterable(excludes)

        args = (
            "borgbackup",
            "--verbose",
            "create",
            *excludes,
            archive,
            "."
        )

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = self.password
        env["BORG_RSH"] = self.sshCommand

        subprocess.run(args, cwd=self.source, env=env, check=True)

class CheckBackups(TaskBase):
    def countOne(self, repository, password):
        args = (
            "borg",
            "list",
            "--json",
            repository
        )

        env = os.environ.copy()
        env["BORG_PASSPHRASE"] = password
        env["BORG_RSH"] = self.sshCommand

        result = subprocess.run(args, env=env, check=True, capture_output=True)

        startDates = map(lambda a: a["start"], json.loads(result.stdout)["archives"])
        startDates = map(datetime.datetime.fromisoformat, startDates)

        today = datetime.date.today()
        return sum(map(lambda d: 1 if d.date() == today else 0, startDates))

    def execute(self):
        def formatLine(repo):
            numBackups = self.countOne(repo["url"], repo["password"])
            return "{}: {} (today)".format(repo["name"], numBackups)
        lines = [formatLine(repo) for repo in self.repositories]

        self.notify.send("Backup check results:\n{} ".format("\n".join(lines)))

class Config(object):
    TASK_FACTORIES={
        "testfail" : TestFailTask,
        "rclone"   : RcloneTask,
        "backup"   : BackupTask,
        "check"    : CheckBackups
    }

    def __init__(self, tomlFile):
        self._config = toml.load(tomlFile)
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
            conf = copy.copy(self._config.get(tType, {}))
            conf.update(taskConf)
            conf["notify"] = self.notify
            return Config.TASK_FACTORIES[tType](**conf)

        return list(map(make_task, self._config.get("tasks", [])))

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
    config = Config(sys.argv[1])

    numFailed = sum(map(lambda t: t.safe_execute(), config.tasks))

    if numFailed == 0:
        config.notify.send("Backup successful")
