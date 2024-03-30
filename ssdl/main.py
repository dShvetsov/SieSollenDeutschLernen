import telebot
from telebot import asyncio_filters
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
import asyncio
import pydantic_settings
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from langchain.chat_models import ChatOpenAI
from openai import AsyncOpenAI

from .apps.ping import Ping
from .apps.chat_helper import ChatHelper
from .apps.login import LogIn


telebot.logger.setLevel(logging.DEBUG) # Outputs debug messages to console.



class TelegramSettings(pydantic_settings.BaseSettings):
    api_key: str

    class Config:
        env_prefix = "TELEGRAM_BOT_"


def main():

    gpt4 = ChatOpenAI(temperature=0, model='gpt-4')
    openai_client = AsyncOpenAI()
    bot = AsyncTeleBot(TelegramSettings().api_key, state_storage=StateMemoryStorage())
    # bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    asyncio.run(bot.set_webhook())

    client = AsyncIOMotorClient('mongodb://ssdl-mongo:27017/')
    db = client.SieSollenDeutschLernen

    ping_app = Ping(bot, db)
    chat_helper = ChatHelper(bot, db, gpt4, openai_client)
    login = LogIn(bot, db)

    bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    bot.add_custom_filter(asyncio_filters.ChatFilter())
    asyncio.run(bot.infinity_polling())


if __name__ == '__main__':
    main()
