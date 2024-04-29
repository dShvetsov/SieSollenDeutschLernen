import asyncio
import os

from ssdl.teleapp import TeleApp, handler, Self
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from motor.motor_asyncio import AsyncIOMotorDatabase as Database
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers.string import StrOutputParser
from openai import AsyncOpenAI

from telebot.asyncio_handler_backends import State, StatesGroup
from langchain_core.prompts.chat import ChatPromptTemplate
import textwrap

class WordsState(StatesGroup):
    populating_word_base = State()
    exercise = State()

class Words(TeleApp):
    name = 'wordbase'

    def __init__(self, bot: AsyncTeleBot, db: Database, chat: ChatOpenAI):
        super().__init__(bot, db)
        self._bot = bot
        self._db = db
        self._chat = chat
        self._populate_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', 'You are helpful assistant knowledgeable in German language'),
                ('human', 'For the word or phrase provided in a German, English or Russian language, '
                          'with a potential typos, give an information about this word, '
                          'including it\'s translation and auxiliary information such as gender '
                          'of the word, or how the word in used in a sentences.'),
                ('ai', textwrap.dedent(
                    '''der Hauptbahnhof: the central train station (центральный вокзал).

                    The word consist out of two parts:
                    1. Haupt - Main
                    2. Bahnhof - Train station'''
                   ),
                ),
                ('user', '{word}')
            ]
        )
        self._populate_chain = self._populate_prompt | self._chat | StrOutputParser()
        self._exercise_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', 'Du bist ein hilfreicher Assistent.'),
                ('human', 'Erstelle einen Satz, der das Wort {word} verwendet. Die Komplexität des Satzes sollte dem Niveau B1 entsprechen.')
            ]
        )
        self._translate_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', 'You are helpful assistant'),
                ('human', 'Translate the sentence "{sentence}" in English')
            ]
        )
        self._exercise_chain = self._exercise_prompt | self._chat | StrOutputParser() | {
            'groundtruth': RunnablePassthrough(),
            'exercise': self._translate_prompt | self._chat | StrOutputParser()
        }

        self._check_prompt = ChatPromptTemplate.from_messages([
            ('system', 'You are helpful assistant'),
            ('human', 'List all mistakes, that were made in translation from German to English.\n'
                       'English: "{english}".\German: "{german}"')
        ])
        self._check_chain = self._check_prompt | self._chat | StrOutputParser()

    @handler.message_handler(chat_types='private', commands='words')
    @TeleApp.requires_login
    async def start_populating_wordbase(self, message):
        await self._bot.set_state(
            message.from_user.id, WordsState.populating_word_base, message.chat.id
        )
        await self._bot.reply_to(message, 'You can type words that you want to learn')

    @handler.message_handler(chat_types='private', commands='finish', state=WordsState.populating_word_base)
    async def stop_populating_wordbase(self, message):
        await self._bot.delete_state(message.from_user.id, message.chat.id)
        await self._bot.reply_to(message, 'It is done with populating database')

    @handler.message_handler(chat_types='private', state=WordsState.populating_word_base)
    async def populate_wordbase(self, message):
        word = message.text
        llm_answer = await self._populate_chain.ainvoke(
            {'word': word}
        )
        await self._db.words.insert_one(
            {
                'user_id': message.from_user.id,
                'word': word,
                'llm': llm_answer
            }
        )
        await self._bot.reply_to(message, llm_answer)

    async def exercise(self, user_id):
        cursor = self._db.words.aggregate([
            {'$match': {'user_id': user_id}},
            {'$sample': {'size': 1}}
        ])
        async for word in cursor:
            task = await self._exercise_chain.ainvoke({'word': word})
            await self._bot.set_state(user_id, WordsState.exercise, user_id)
            async with self._bot.retrieve_data(user_id, user_id) as data:
                data['task'] = task
            await self._bot.send_message(
                user_id,
                f'Translate to german: \n\n {task["exercise"]}'
            )

    @handler.message_handler(chat_types='private', state=WordsState.exercise)
    async def check_translation(self, message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        async with self._bot.retrieve_data(user_id, chat_id) as data:
            task = data['task']

        translation = message.text
        llm_answer = await self._check_chain.ainvoke({
            'english': task['exercise'],
            'german': translation
        })
        await self._bot.reply_to(message, llm_answer)
