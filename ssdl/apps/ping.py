from ssdl.teleapp import TeleApp, handler


class Ping(TeleApp):
    name = 'ping'
    def __init__(self, bot, db):
        super().__init__(bot, db)
        self._bot = bot

    @handler.message_handler(commands=['ping'])
    @TeleApp.requires_login
    async def ping(self, message):
        await self._bot.reply_to(message, 'pong')

    async def exercise(self, user_id):
        await self._bot.send_message(user_id, 'hello')
