from telebot import asyncio_filters
import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
import asyncio
from ssdl.exercises import strong_verbs
from ssdl import chat_helper
import pydantic_settings
import logging
from pymongo import MongoClient

telebot.logger.setLevel(logging.DEBUG) # Outputs debug messages to console.

class TelegramSettings(pydantic_settings.BaseSettings):
    api_key: str

    class Config:
        env_prefix = "TELEGRAM_BOT_"

bot = AsyncTeleBot(TelegramSettings().api_key, state_storage=StateMemoryStorage())

strong_verbs.register_handlers(bot)
chat_helper.register_handlers(bot)


bot.add_custom_filter(asyncio_filters.StateFilter(bot))
asyncio.run(bot.set_webhook())


client = MongoClient('mongodb://ssdl-mongo:27017/')
db = client['SieSollenDeutschLernen']
subscribers_collection = db['chat_helpers_subscribers']


@bot.message_handler(chat_types='groups', commands=['test_subscribe'])
async def subscribe(message):
    # Create a subscriber document
    subscriber = {
        "user_id": message.from_user.id,
        "chat_id": message.chat.id
    }

    # Insert the subscriber into the collection, avoiding duplicates
    subscribers_collection.update_one(subscriber, {'$setOnInsert': subscriber}, upsert=True)

    # Send a confirmation message
    await bot.reply_to(message, 'You were subscribed')


def main():

    @bot.message_handler(commands=['ping'])
    async def ping(message):
        await bot.reply_to(message, 'pong')

    asyncio.run(bot.infinity_polling())


if __name__ == '__main__':
    main()
