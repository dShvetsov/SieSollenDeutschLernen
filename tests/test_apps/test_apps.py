import pytest
from unittest import mock

from ssdl.apps.ping import Ping
from ssdl.apps.chat_helper import ChatHelper


class TestPing:

    @pytest.mark.asyncio
    async def test_ping(self, async_telebot, message):
        p = Ping(async_telebot)
        await p.ping(message)
        async_telebot.reply_to.assert_called_once_with(message, 'pong')

class TestChatHelper:

    @pytest.fixture
    def chat_helper(self, async_telebot, mongo_db):
        return ChatHelper(async_telebot, mongo_db)

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

        subscr = mongo_db.chat_helpers_subscribers.find_one(subscriber)
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

        subscr = mongo_db.chat_helpers_subscribers.find_one(subscriber)
        assert subscr['subscribed'] == False

    def test_is_subscribed_no_entry(self, message, chat_helper):
        assert not chat_helper.is_subscribed(message)

    @pytest.mark.asyncio
    async def test_is_subscribed(self, message, chat_helper):
        await chat_helper.subscribe(message)
        assert chat_helper.is_subscribed(message)

    @pytest.mark.asyncio
    async def test_is_subscribed_unsubscribed(self, message, chat_helper):
        await chat_helper.subscribe(message)
        await chat_helper.unsubscribe(message)
        assert not chat_helper.is_subscribed(message)
