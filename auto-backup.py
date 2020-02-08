#!/usr/bin/env python

import sys
import toml
import asyncio
import aioxmpp

class Config(object):
    def __init__(self, tomlFile):
        self._config = toml.load(tomlFile)

    @property
    def account_name(self):
        return self._config["XMPP"]["account"]

    @property
    def password(self):
        return self._config["XMPP"]["password"]

    @property
    def recipient(self):
        return self._config["XMPP"]["recipient"]

async def send_notification(sender, password, recipient, msgStr):
    jid = jid = aioxmpp.JID.fromstr(sender)
    sec_layer = aioxmpp.make_security_layer(password)
    recipient_jid = aioxmpp.JID.fromstr(recipient)

    client = aioxmpp.PresenceManagedClient(jid, sec_layer)

    async with client.connected() as stream:
        msg = aioxmpp.Message(to=recipient_jid, type_=aioxmpp.MessageType.CHAT)

        msg.body[None] = msgStr

        await client.send(msg)

if __name__ == "__main__":
    config = Config(sys.argv[1])

    msg = "XMPP Hello World!"

    asyncio.run(send_notification(config.account_name, config.password, config.recipient, msg))
