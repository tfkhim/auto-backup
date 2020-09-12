import asyncio

import aioxmpp


class XMPPnotifications(object):
    def __init__(self, account, password, recipient):
        self.sender = account
        self.password = password
        self.recipient = recipient

    def send(self, message):
        asyncio.run(self._async_send(message))

    async def _async_send(self, message):
        client = self._setup_client()
        message = self._prepare_message(message)
        await self._connect_and_send(client, message)

    def _setup_client(self):
        jid = aioxmpp.JID.fromstr(self.sender)
        sec_layer = aioxmpp.make_security_layer(self.password)

        return aioxmpp.PresenceManagedClient(jid, sec_layer)

    def _prepare_message(self, message):
        recipient_jid = aioxmpp.JID.fromstr(self.recipient)
        xmpp_msg = aioxmpp.Message(to=recipient_jid, type_=aioxmpp.MessageType.CHAT)
        xmpp_msg.body[None] = message
        return xmpp_msg

    async def _connect_and_send(self, client, message):
        async with client.connected() as stream:
            await stream.send(message)
