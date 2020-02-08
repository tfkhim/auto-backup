#!/usr/bin/env python

import sys
import toml
import asyncio
import aioxmpp
import datetime

class Config(object):
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
        return list(self._config["tasks"])

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

class RcloneTask(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return self.name

    def execute(self):
        pass

def create_task(config):
    typeMap = {
        "rclone" : RcloneTask
    }
    return typeMap[config["type"]](**config)

if __name__ == "__main__":
    config = Config(sys.argv[1])
    notify = Notifications(config)

    tasks = list(map(create_task, config.tasks))

    for task in tasks:
        task.execute()

    notify.send("Backup successful")
