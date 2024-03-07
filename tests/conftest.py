import pytest
from unittest import mock
import mongomock


@pytest.fixture
def async_telebot():

    bot = mock.MagicMock()
    bot.reply_to = mock.AsyncMock()
    return bot


@pytest.fixture
def message():
    m = mock.AsyncMock()
    m.from_user.id = 1
    m.chat.id = 1000
    return m


@pytest.fixture
def mongo_client():
    return mongomock.MongoClient()

@pytest.fixture
def mongo_db(mongo_client):
    return mongo_client['db']
