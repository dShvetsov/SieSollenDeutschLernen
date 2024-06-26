import telebot
from telebot import asyncio_filters
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
import asyncio
import pydantic_settings
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from .apps.ping import Ping
from .apps.chat_helper import ChatHelper
from .apps.login import LogIn
from .apps.words import Words
from .apps.LearningPlan import LearningPlan


telebot.logger.setLevel(logging.DEBUG) # Outputs debug messages to console.



class TelegramSettings(pydantic_settings.BaseSettings):
    api_key: str
    class Config:
        env_prefix = "TELEGRAM_BOT_"


class MongoDBSettings(pydantic_settings.BaseSettings):
    port: int
    username: str
    password: str

    class Config:
        env_prefix = 'MONGODB_'



def main():

    gpt4 = ChatOpenAI(temperature=0, model='gpt-4')
    openai_client = AsyncOpenAI()
    bot = AsyncTeleBot(TelegramSettings().api_key, state_storage=StateMemoryStorage())
    # bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    asyncio.run(bot.set_webhook())

    settings = MongoDBSettings()
    client = AsyncIOMotorClient(
        f'mongodb://{settings.username}:{settings.password}@ssdl-mongo:{settings.port}/',

    )
    db = client.SieSollenDeutschLernen

    scheduler = AsyncIOScheduler()

    ping_app = Ping(bot, db)
    chat_helper = ChatHelper(bot, db, gpt4, openai_client)
    login = LogIn(bot, db)
    wordbase = Words(bot, db, gpt4)

    learning_plan = LearningPlan(bot, db, scheduler, ping_app, wordbase)

    async def _main():
        scheduler.start()
        learning_plan.schedule_plan()
        await bot.infinity_polling()

    bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    bot.add_custom_filter(asyncio_filters.ChatFilter())
    asyncio.run(_main())


if __name__ == '__main__':
    main()
