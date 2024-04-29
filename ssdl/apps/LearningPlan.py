import asyncio
import json
import io

from ssdl.teleapp import TeleApp, handler, Self
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from motor.motor_asyncio import AsyncIOMotorDatabase as Database

from apscheduler.schedulers.asyncio import AsyncIOScheduler

class LearningPlan(TeleApp):

    def __init__(self, bot: AsyncTeleBot, db: Database, scheduler: AsyncIOScheduler, *apps):
        super().__init__(bot, db)
        with open('./data/learning_plan.json') as f:
            self._learning_plan = json.load(f)
        self._bot = bot
        self._scheduler = scheduler
        self._apps = {a.name: a for a in apps}
        self._db = db

    def schedule_plan(self):
        self._scheduler.pause()
        self._scheduler.remove_all_jobs()
        for user, user_plan in self._learning_plan.items():
            user = int(user)
            for exercise, exercise_plan in user_plan.items():
                application = self._apps[exercise]
                for event in exercise_plan:
                    assert event['trigger'] == 'cron'
                    self._scheduler.add_job(
                        application.exercise, event['trigger'], **event['parameters'],
                        args=[user]
                    )
        self._scheduler.resume()

    @staticmethod
    async def async_hello(bot, user_id, chat_id):
        print(f"Scheduler message for {user_id=}, {chat_id=}")
        await bot.send_message(chat_id, text='Hallo')

    @handler.message_handler(commands=['schedule'])
    async def schedule(self, message: Message):
        self._scheduler.add_job(
            self.async_hello,
            'interval',
            seconds=5,
            kwargs={'bot': self._bot, 'user_id': message.from_user.id, 'chat_id': message.chat.id}
        )

