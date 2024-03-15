import pytest
from unittest import mock

from ssdl.apps.ping import Ping
from ssdl.apps.chat_helper import ChatHelper


class ANY:
    def __eq__(self, actual):
        return True

class TestPing:

    @pytest.mark.asyncio
    async def test_ping(self, async_telebot, message):
        p = Ping(async_telebot)
        await p.ping(message)
        async_telebot.reply_to.assert_called_once_with(message, 'pong')

class TestChatHelper:

    @pytest.fixture
    def chat_helper(self, async_telebot, mongo_db):
        gpt4 = mock.MagicMock()
        gpt4.ainvoke = mock.AsyncMock()
        return ChatHelper(async_telebot, mongo_db, gpt4)

    @pytest.mark.asyncio
    async def test_subscribe(self, chat_helper, message, async_telebot, mongo_db):
        await chat_helper.subscribe(message)

        async_telebot.reply_to.assert_called_once_with(
            message, mock.ANY
        )

        subscriber = {
            'user_id': 1,
            'chat_id': 1000
        }

        subscr = await mongo_db.chat_helpers_subscribers.find_one(subscriber)
        assert subscr['subscribed'] == True

    @pytest.mark.asyncio
    async def test_unsubscribe(self, chat_helper, message, async_telebot, mongo_db):
        await chat_helper.unsubscribe(message)

        async_telebot.reply_to.assert_called_once_with(
            message, mock.ANY
        )

        subscriber = {
            'user_id': 1,
            'chat_id': 1000
        }

        subscr = await mongo_db.chat_helpers_subscribers.find_one(subscriber)
        assert subscr['subscribed'] == False

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_is_subscribed_no_entry(self, message, chat_helper):
        assert not await chat_helper.is_subscribed(message)

    @pytest.mark.asyncio
    async def test_is_subscribed(self, message, chat_helper):
        await chat_helper.subscribe(message)
        assert await chat_helper.is_subscribed(message)

    @pytest.mark.asyncio
    async def test_is_subscribed_unsubscribed(self, message, chat_helper):
        await chat_helper.subscribe(message)
        await chat_helper.unsubscribe(message)
        assert not await chat_helper.is_subscribed(message)

    @pytest.mark.asyncio
    async def test_analyze_mistakes(self, message, chat_helper, mongo_db):
        message.json = {
            'chat_id': 1000,
            'user_id': 1,
            'text': 'Text os the message',
            'message_id': 123
        }
        await chat_helper.analyze_mistakes(message)
        assert await mongo_db.messages.find_one({'message_id': 123}) == {
            '_id': ANY(),
            'chat_id': 1000,
            'user_id': 1,
            'text': 'Text os the message',
            'message_id': 123
        }

    @pytest.mark.asyncio
    async def test_is_reply_to_bot(self, message, chat_helper):
        message.reply_to_message.from_user.id = 807
        assert chat_helper.is_reply_to_bot(message)

    @pytest.mark.asyncio
    async def test_is_reply_to_bot_not(self, message, chat_helper):
        message.reply_to_message.from_user.id = 806
        assert not chat_helper.is_reply_to_bot(message)

    @pytest.mark.asyncio
    async def test_is_reply_to_bot_not_reply_at_all(self, message, chat_helper):
        message.reply_to_message = mock.Mock(return_value=None)
        assert not chat_helper.is_reply_to_bot(message)
