#!/usr/bin/env python

import sys
import asyncio
import aioxmpp

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
    msg = "XMPP Hello World!"

    import getpass
    password = getpass.getpass()

    asyncio.run(send_notification(sys.argv[1], password, sys.argv[2], msg))
