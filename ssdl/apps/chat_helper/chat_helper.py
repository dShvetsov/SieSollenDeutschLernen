from ssdl.teleapp import TeleApp, handler
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from pymongo.database import Database


class ChatHelper(TeleApp):
    groups = ['group', 'subgroup', 'supergroup']

    def __init__(self, bot: AsyncTeleBot, db: Database):
        super().__init__(bot)
        self._bot = bot
        self._db = db
        self._subscribers_collection = self._db['chat_helpers_subscribers']

    @handler.message_handler(chat_types=groups, commands=['subscribe'])
    async def subscribe(self, message: Message):
        subscriber = {
            'user_id': message.from_user.id,
            'chat_id': message.chat.id
        }
        self._subscribers_collection.update_one(
            subscriber, {'$set': {'subscribed': True}},  upsert=True
        )
        await self._bot.reply_to(message, 'You were subscrubed, to unsubscribe type /unsubscribe')

    @handler.message_handler(chat_types=groups, commands=['unsubscribe'])
    async def unsubscribe(self, message):
        subscriber = {
            'user_id': message.from_user.id,
            'chat_id': message.chat.id
        }
        self._subscribers_collection.update_one(
            subscriber, {'$set': {'subscribed': False}},  upsert=True
        )

        await self._bot.reply_to(message, 'You were unsubscrubed, to unsubscribe type /subscribe')

    def is_subscribed(self, message):
        subscriber = {
            'user_id': message.from_user.id,
            'chat_id': message.chat.id
        }
        user = self._subscribers_collection.find_one(subscriber)
        if user:
            return user['subscribed']
        else:
            return False
