import asyncio
import io

from openai import AsyncOpenAI

from telebot.async_telebot import AsyncTeleBot
import json
import os
import logging

from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.chat_models import ChatOpenAI
chat = ChatOpenAI(temperature=0)
openai_client = AsyncOpenAI()

subscribers_file = './subscribers.json'
if os.path.isfile(subscribers_file):
    with open(subscribers_file, 'r') as f:
        subscribers = set(map(tuple, json.load(f)))
else:
    subscribers = set()

chat = ChatOpenAI(temperature=0, model='gpt-4')

groups = ['group', 'subgroup', 'supergroup']

message_memory = dict()


def create_query_to_bot(message):
    messages = [
        SystemMessage(
            content="You're a helpful assistant, that helps student to learn German"),
        HumanMessage(
            content="List all mistakes that have been made in the text. If there is no mistake output no mistakes: \n\n" + \
                f"{message.text}"
            )
    ]
    return messages



def create_messages_from_thread(m_id):
    message, initial = message_memory[m_id]
    if initial:
        return create_query_to_bot(message)
    else:
        if message.reply_to_message is None:
            raise RuntimeError('not initial message without replies')
        messages = create_messages_from_thread(message.reply_to_message.id)
        if message.from_user.is_bot:
            messages.append(AIMessage(content=message.text))
        else:
            messages.append(HumanMessage(content=message.text))
        return messages


def register_handlers(bot: AsyncTeleBot):

    bot_id = asyncio.run(bot.get_me()).id

    def reply_to_bot_message(message):
        if message.reply_to_message is not None:
             whom_replied = message.reply_to_message.from_user
             return whom_replied.id == bot_id
        else:
             return False

    @bot.message_handler(chat_types=groups, commands=['subscribe'])
    async def subscribe(message):
        subscribers.add((message.from_user.id, message.chat.id))
        with open(subscribers_file, 'w') as f:
            json.dump(list(subscribers), f)
        await bot.reply_to(message, 'You were subscribed')

    @bot.message_handler(chat_types=groups, commands=['unsubscribe'])
    async def unsubscribe(message):
        subscribers.remove((message.from_user.id, message.chat.id))
        with open(subscribers_file, 'w') as f:
            json.dump(list(subscribers), f)
        await bot.reply_to(message, 'You were unsubscribed')

    @bot.message_handler(chat_types=groups, content_types='text', func=reply_to_bot_message)
    async def speak_with_bot(message):
        try:
            message_memory[message.id] = (message, False)
            messages = create_messages_from_thread(message.id)
            logging.info(messages)
            model_answer = await chat.ainvoke(messages)
            reply = await bot.reply_to(message, model_answer.content)
            message_memory[reply.id] = (reply, False)
        except Exception as e:
            reply = await bot.reply_to(message, f"Something bad happend: {e}") 
            message_memory[reply.id] = (reply, False)

    @bot.message_handler(chat_types=groups, func=lambda m: (m.from_user.id, m.chat.id) in subscribers)
    async def help_with_mistakes(message):
        message_memory[message.id] = (message, True)
        messages = create_query_to_bot(message)
        model_answer = await chat.ainvoke(messages)
        reply = await bot.reply_to(message, model_answer.content)
        message_memory[reply.id] = (reply, False)

    @bot.message_handler(chat_types=groups, content_types='voice', func=lambda m: (m.from_user.id, m.chat.id) in subscribers)
    async def voice_help_with_mistakes(message):
        voice = message.voice
        if voice.file_size > 715000 or voice.duration > (5 * 60):
            reply = await bot.reply_to(message, 'The voice is too large')
            return

        file = await bot.get_file(voice.file_id)

        file_bytes = await bot.download_file(file.file_path)
        stream = io.BytesIO(file_bytes)
        transcript = await openai_client.audio.transcriptions.create(
            model='whisper-1',
            file=(file.file_path, stream),
            response_format='text'
        )
        message.text = transcript
        message_memory[message.id] = (message, True)
        messages = create_query_to_bot(message)
        model_answer = await chat.ainvoke(messages)

        reply_text = '-' * 5 + ' transcript ' + '-' * 5 + '\n' + transcript + 15 * '-' + '\n' + model_answer.content

        reply = await bot.reply_to(message, reply_text)
        message_memory[reply.id] = (reply, False)
