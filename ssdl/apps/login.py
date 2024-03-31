import base64
import uuid
import os
from datetime import datetime
import textwrap

from pydantic import BaseModel, Field

from ssdl.teleapp import TeleApp, handler, Self
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
import telebot.types
from telebot.asyncio_filters import AdvancedCustomFilter
from motor.motor_asyncio import AsyncIOMotorClient as Database

from telebot.asyncio_handler_backends import State, StatesGroup
from telebot.util import quick_markup


def fix_paragraphes(s):
    uniq_str = '<NEWLINE>'
    s = s.replace('\n\n', uniq_str)
    s = s.replace('\n', '')
    return s.replace(uniq_str, '\n')


class InvitationCode(BaseModel):
    code: str = Field(..., min_length=8, max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used: bool = Field(default=False)


class LoginStates(StatesGroup):
    wait_for_code = State()
    wait_for_confirmation = State()


class IsUserFilter(AdvancedCustomFilter):
    key='username'
    async def check(self, message, text):
        return message.from_user.username == text


class LogIn(TeleApp):
    ADMIN_USER = os.environ['SSDL_ADMIN']

    def __init__(self, bot: AsyncTeleBot, db: Database):
        super().__init__(bot, db)
        self._bot = bot
        self._bot.add_custom_filter(IsUserFilter())
        self._db = db

    @handler.message_handler(commands=['signin', 'login', 'start'])
    async def login(self, message):
        login_message = textwrap.dedent('''
            This is alpha version of Sie Sollen Deutsch Lernen Bot.

            This bot can be used only by invitation, if you already have an
            invitation code, please send it to the chat.

            If you don't have the code yet, please write the admin of the bot.

            If you don't know whom you should write, probably you don't need to use the
            bot yet, and should wait for the release
        ''')
        login_message = fix_paragraphes(login_message)
        user_id = message.from_user.id
        found_user = await self._db.registered_users.find_one({'id': user_id})
        if found_user:
            await self._bot.reply_to(message, "You're already logged in")
        else:
            await self._bot.reply_to(message, login_message)
            await self._bot.set_state(
                user_id, LoginStates.wait_for_code, message.chat.id
            )

    @handler.message_handler(commands=['cancel'], state=LoginStates.wait_for_code)
    async def cancel_signin(self, message):
        await self._bot.delete_state(message.from_user.id, message.chat.id)
        await self._bot.reply_to(message, 'ok')

    def yesno_keyboard(self):
        markup = ReplyKeyboardMarkup(row_width=2, is_persistent=True)
        markup.add(
            KeyboardButton('Yes'),
            KeyboardButton('No')
        )
        return markup

    @handler.message_handler(state=LoginStates.wait_for_code)
    async def wait_for_code(self, message: Message):
        code = message.text
        codes_db = self._db.invitation_codes
        invitation_code = await codes_db.find_one({'code': message.text})
        user_id = message.from_user.id
        chat_id = message.chat.id
        confirm_message = textwrap.dedent('''
            Confirmation code is accepted.

            Please note that the bot is powered by gpt, that means that
            messages, that you send to it will be send to openai.gpt to
            be analyzed, also messages that you send to the bot will be stored
            in a database, so we can workout on the study plan based on
            their analysis. As well the bot implements chat helpers, and being
            added to the chat it may also analyze and store the messaged.



            Do you want to continue?
        ''')
        if not invitation_code:
            await self._bot.reply_to(
                message,
                'This is an invalid code'
            )
            return
        elif invitation_code['used']:
            await self._bot.reply_to(
                message,
                'You are trying to use the code, that has already been used. ' +
                'Ask for another one'
            )
            return
        else:
            async with self._bot.retrieve_data(user_id, chat_id) as data:
                data['confirmation_code'] = code

            markup = self.yesno_keyboard()
            await self._bot.set_state(user_id, LoginStates.wait_for_confirmation, chat_id)
            await self._bot.reply_to(
                message,
                confirm_message,
                reply_markup=markup
            )

    @handler.message_handler(state=LoginStates.wait_for_confirmation)
    async def wait_for_confirmation(self, message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        markup = telebot.types.ReplyKeyboardRemove()
        if message.text == 'No':
            await self._bot.reply_to(
                message,
                'Understandable, have a nice day',
                reply_markup=markup
            )
            return
        elif message.text == 'Yes':
            msg = await self._bot.reply_to(message,
                                           'Great you will be registered in a moment, please wait...',
                                           reply_markup=markup)
            async with self._bot.retrieve_data(user_id, chat_id) as data:
                code = data['confirmation_code']
            codes_db = self._db.invitation_codes
            await codes_db.update_one({'code': code}, {'$set': {'used': True}})
            await self._db.registered_users.insert_one(message.from_user.to_dict())
            await self._bot.delete_state(message.from_user.id, message.chat.id)
            await self._bot.reply_to(
                msg,
                'Perfect, you have been registered, now you can use the bot',
            )

    def generate_code(self):
        return str(uuid.uuid4())[:8]

    @handler.message_handler(commands=['invite'], username=ADMIN_USER)
    async def generate_invitation_code(self, message):
        invitation = InvitationCode(code=self.generate_code())
        await self._db.invitation_codes.insert_one(invitation.dict())
        await self._bot.reply_to(message, invitation.code)
