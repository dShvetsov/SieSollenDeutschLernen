import asyncio

from ssdl.teleapp import TeleApp, handler, Self
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
        self._messages_collection = self._db['messages']
        self._bot_id = asyncio.run(bot.get_me()).id

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
    async def unsubscribe(self, message: Message):
        subscriber = {
            'user_id': message.from_user.id,
            'chat_id': message.chat.id
        }
        self._subscribers_collection.update_one(
            subscriber, {'$set': {'subscribed': False}},  upsert=True
        )

        await self._bot.reply_to(message, 'You were unsubscrubed, to unsubscribe type /subscribe')

    def is_subscribed(self, message: Message) -> bool:
        subscriber = {
            'user_id': message.from_user.id,
            'chat_id': message.chat.id
        }
        user = self._subscribers_collection.find_one(subscriber)
        if user:
            return user['subscribed']
        else:
            return False

    def is_reply_to_bot(self, message: Message) -> bool:
        if message.reply_to_message is not None:
            replied_to = message.reply_to_message.from_user
            return replied_to.id == self._bot_id
        else:
            return False

    def save_message(self, message: Message):
        dump = message.json
        self._db.messages.insert_one(dump)

    @handler.message_handler(chat_types=groups, func=Self('is_subscribed'))
    async def analyze_mistakes(self, message):
        self.save_message(message)
        await self._bot.reply_to(message, 'Just imagine that I helped you')
