#!/usr/bin/env python

import sys
import toml
import asyncio
import aioxmpp
import datetime

class TaskBase(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return self.name

class TestFailTask(TaskBase):
    def execute(self):
        raise RuntimeError("Task failed")

class RcloneTask(TaskBase):
    def execute(self):
        pass

class Config(object):
    TASK_FACTORIES={
        "testfail" : TestFailTask,
        "rclone"   : RcloneTask
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
            factory = Config.TASK_FACTORIES[taskConf["type"]]
            return factory(**taskConf)

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

def safe_execute(task, notify):
    try:
        task.execute()
        return 0
    except:
        notify.send("Task failed: {}".format(task))
        return 1

if __name__ == "__main__":
    config = Config(sys.argv[1])
    notify = Notifications(config)

    numFailed = sum(map(lambda t: safe_execute(t, notify), config.tasks))

    if numFailed == 0:
        notify.send("Backup successful")
