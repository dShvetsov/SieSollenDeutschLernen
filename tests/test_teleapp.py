from ssdl.teleapp import TeleApp, handler, Self
import pytest
from unittest import mock

class Test_TeleApp:

    class Dummy(TeleApp):

        def __init__(self, bot):
            super().__init__(bot)

        @handler.message_handler('arg', kwarg='kwarg')
        def function(self, message):
            pass

    class AsyncDummy(TeleApp):

        def __init__(self, bot):
            super().__init__(bot)

        @handler.message_handler('arg', kwarg='kwarg')
        async def function(self, message):
            pass

    @pytest.mark.parametrize(
        'App', [Dummy, AsyncDummy]
    )
    def test_teleapp(self, App):

        bot = mock.MagicMock()
        app = App(bot)

        bot.message_handler.assert_called_once_with(
            'arg', kwarg='kwarg'
        )

        bot.message_handler.return_value.assert_called_once_with(
            app.function
        )

    def test_Self(self):

        class App(TeleApp):
            def __init__(self, bot):
                super().__init__(bot)

            def _internal(self):
                pass

            @handler.message_handler(Self('_internal'), func=Self('_internal'))
            def function(self, message):
                pass

        bot = mock.MagicMock()
        app = App(bot)
        bot.message_handler.asssert_called_once_with(
            app._internal, func=app._internal
        )
