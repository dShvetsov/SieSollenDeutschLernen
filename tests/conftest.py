import pytest
from unittest import mock
from mongomock_motor import AsyncMongoMockClient


@pytest.fixture
def async_telebot():

    bot = mock.MagicMock()
    bot.reply_to = mock.AsyncMock()
    bot.get_me = mock.AsyncMock()
    bot.get_me.return_value.id = 807
    return bot


@pytest.fixture
def message():
    m = mock.MagicMock()
    m.from_user.id = 1
    m.chat.id = 1000
    return m


@pytest.fixture
def mongo_client():
    return AsyncMongoMockClient()

@pytest.fixture
def mongo_db(mongo_client):
    return mongo_client['db']
