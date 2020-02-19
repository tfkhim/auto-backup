#!/usr/bin/env python

import os
import sys
import toml
import copy
import asyncio
import aioxmpp
import datetime
import itertools
import traceback
import subprocess

class TaskBase(object):
    def __init__(self, *, name, **kwargs):
        self.name = name

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return self.name

    def safe_execute(self, notify):
        try:
            self.execute()
            return 0
        except:
            traceback.print_exc()
            notify.send("Task failed: {}".format(self))
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

class Config(object):
    TASK_FACTORIES={
        "testfail" : TestFailTask,
        "rclone"   : RcloneTask,
        "backup"   : BackupTask
    }

    def __init__(self, tomlFile):
        self._config = toml.load(tomlFile)

    @property
    def account(self):
        return self._config["XMPP"]["account"]

    @property
    def password(self):
        return self._config["XMPP"]["password"]

    @property
    def recipient(self):
        return self._config["XMPP"]["recipient"]

    @property
    def tasks(self):
        def make_task(taskConf):
            tType = taskConf["type"]
            conf = copy.copy(self._config.get(tType, {}))
            conf.update(taskConf)
            return Config.TASK_FACTORIES[tType](**conf)

        return list(map(make_task, self._config.get("tasks", [])))

class Notifications(object):
    def __init__(self, config):
        self.sender = config.account
        self.password = config.password
        self.recipient = config.recipient

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
    notify = Notifications(config)

    numFailed = sum(map(lambda t: t.safe_execute(notify), config.tasks))

    if numFailed == 0:
        notify.send("Backup successful")
