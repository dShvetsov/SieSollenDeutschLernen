from ssdl.teleapp import TeleApp, handler


class Ping(TeleApp):
    def __init__(self, bot):
        super().__init__(bot)
        self._bot = bot

    @handler.message_handler(commands=['ping'])
    async def ping(self, message):
        await self._bot.reply_to(message, 'pong')
