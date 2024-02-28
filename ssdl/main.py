from telebot import asyncio_filters
import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
import asyncio
from exercises import strong_verbs
import chat_helper
import pydantic_settings
import logging

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

if __name__ == '__main__':
    asyncio.run(bot.infinity_polling())
