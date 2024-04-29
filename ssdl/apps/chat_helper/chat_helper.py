import asyncio
import io

from ssdl.teleapp import TeleApp, handler, Self
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from motor.motor_asyncio import AsyncIOMotorDatabase as Database
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI



class ChatHelper(TeleApp):
    groups = ['group', 'subgroup', 'supergroup']

    def __init__(self, bot: AsyncTeleBot, db: Database, chat: ChatOpenAI, openai_client: AsyncOpenAI):
        super().__init__(bot, db)
        self._bot = bot
        self._db = db
        self._subscribers_collection = self._db['chat_helpers_subscribers']
        self._messages_collection = self._db['messages']
        self._bot_id = asyncio.run(bot.get_me()).id
        self._chat = chat
        self._openai_client = openai_client

    @handler.message_handler(chat_types=groups, commands=['subscribe'])
    async def subscribe(self, message: Message):
        subscriber = {
            'user_id': message.from_user.id,
            'chat_id': message.chat.id
        }
        await self._subscribers_collection.update_one(
            subscriber, {'$set': {'subscribed': True}},  upsert=True
        )
        await self._bot.reply_to(message, 'You were subscrubed, to unsubscribe type /unsubscribe')

    @handler.message_handler(chat_types=groups, commands=['unsubscribe'])
    async def unsubscribe(self, message: Message):
        subscriber = {
            'user_id': message.from_user.id,
            'chat_id': message.chat.id
        }
        await self._subscribers_collection.update_one(
            subscriber, {'$set': {'subscribed': False}},  upsert=True
        )

        await self._bot.reply_to(message, 'You were unsubscrubed, to unsubscribe type /subscribe')

    async def is_subscribed(self, message: Message) -> bool:
        subscriber = {
            'user_id': message.from_user.id,
            'chat_id': message.chat.id
        }
        user = await self._subscribers_collection.find_one(subscriber)
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

    async def save_message(self, message: Message):
        dump = message.json
        await self._db.messages.insert_one(dump)

    def create_query_to_bot(self, message):
        # TODO: Test Me
        if message.from_user.id == self._bot_id:
            raise RuntimeError('Bot is trying to assist himself')
        messages = [
            SystemMessage(
                content="You're a helpful assistant, that helps student to learn German"),
            HumanMessage(
                content="List all mistakes that have been made in the text. If there is no mistake output no mistakes: \n\n" + \
                    f"{message.text}"
                )
        ]
        return messages
    
    async def extract_message_from_db(self, message):
        # Because reply_to messages don't contain `reply_to` even if it is a thread
        # We need to restore this messages from the database
        query = {
            'message_id': message.message_id,
            'chat.id': message.chat.id
        }
        found_message_dict = await self._db.messages.find_one(query)
        if not found_message_dict:
            raise RuntimeError('Failed to find the message in the database')
        found_message_dict.pop('_id')
        found_message = Message.de_json(found_message_dict)
        return found_message

    async def unroll_thread(self, message):
        if message.reply_to_message is None:
            return self.create_query_to_bot(message)
        else:
            reply_message = await self.extract_message_from_db(message.reply_to_message)
            lc_messages = await self.unroll_thread(reply_message)
            if message.from_user.id == self._bot_id:
                lc_messages.append(AIMessage(content=message.text))
            else:
                lc_messages.append(HumanMessage(content=message.text))
            return lc_messages
        

    @handler.message_handler(chat_types=groups, func=Self('is_reply_to_bot'))
    async def answer_to_reply(self, message):
        await self.save_message(message)
        lc_messages = await self.unroll_thread(message)
        model_answer = await self._chat.ainvoke(lc_messages)
        reply = await self._bot.reply_to(message, model_answer.content)
        await self.save_message(reply)

    @handler.message_handler(chat_types=groups, func=Self('is_subscribed'))
    async def analyze_mistakes(self, message):
        # TODO: Test Me
        await self.save_message(message)
        lc_messages = self.create_query_to_bot(message)
        model_answer = await self._chat.ainvoke(lc_messages)
        reply = await self._bot.reply_to(message, model_answer.content)
        await self.save_message(reply)

    async def get_voice_stream(self, message):
        voice = message.voice
        if voice.file_size > 715000 or voice.duration > (5 * 60):
            raise ValueError('Size of the voice is too large')
        file = await self._bot.get_file(voice.file_id)

        file_bytes = await self._bot.download_file(file.file_path)
        stream = io.BytesIO(file_bytes)
        return file.file_path, stream

    @handler.message_handler(chat_types=groups, content_types='voice', func=Self('is_subscribed'))
    async def analyze_voice(self, message):
        file_path, stream = await self.get_voice_stream(message)
        transcript = await self._openai_client.audio.transcriptions.create(
            model='whisper-1',
            file=(file_path, stream),
            response_format='text'
        )
        transcript_begin = '-' * 5 + ' transcript ' + '-' * 5
        transcript_end = '-' * 15
        await self._bot.reply_to(message, f'{transcript_begin}\n{transcript}\n{transcript_end}')

        message.text = transcript  # TODO: Is it ok?
        await self.analyze_mistakes(message)
