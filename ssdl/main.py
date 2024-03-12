import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
import asyncio
import pydantic_settings
import logging
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient

from .apps.ping import Ping
from .apps.chat_helper import ChatHelper


telebot.logger.setLevel(logging.DEBUG) # Outputs debug messages to console.



class TelegramSettings(pydantic_settings.BaseSettings):
    api_key: str

    class Config:
        env_prefix = "TELEGRAM_BOT_"


def main():

    bot = AsyncTeleBot(TelegramSettings().api_key, state_storage=StateMemoryStorage())
    # bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    asyncio.run(bot.set_webhook())

    client = AsyncIOMotorClient('mongodb://ssdl-mongo:27017/')
    db = client.SieSollenDeutschLernen

    ping_app = Ping(bot)
    chat_helper = ChatHelper(bot, db)

    asyncio.run(bot.infinity_polling())


if __name__ == '__main__':
    main()
