from functools import wraps
import inspect


class TeleApp:
    def __init__(self, bot, db):
        self.__bot = bot
        self.__db = db
        self.__register(bot)

    def __to_register(self):
        for key in dir(self):
            member = getattr(self, key)
            if hasattr(member, '__teleapp_function'):
                yield member

    def __to_register_sorted(self):
        yield from sorted(
            self.__to_register(),
            key=lambda m: getattr(m, '__teleapp_function').order
        )

    def __register(self, bot):
        for member in self.__to_register_sorted():
            teleapp_function = getattr(member, '__teleapp_function')
            getattr(bot, teleapp_function.method)(
                *teleapp_function.args(self), **teleapp_function.kwargs(self)
            )(member)

    @classmethod
    def requires_login(cls, func):

        async def inner(self, message):
            user_id = message.from_user.id
            found_user = await self.__db.registered_users.find_one({'id': user_id})
            if not found_user:
                await self.__bot.reply_to(message, "You have to be logged in")
                return
            else:
                await func(self, message)

        return inner


class Self:
    def __init__(self, method):
        self._method = method

    @property
    def method(self):
        return self._method


class TeleAppDecorator:
    def __init__(self, method, order, *args, **kwargs):
        self._method = method
        self._args = args
        self._kwargs = kwargs
        self._order = order

    @property
    def method(self):
        return self._method

    @property
    def order(self):
        return self._order

    def _transform(self, argument, obj):
        if isinstance(argument, Self):
            return getattr(obj, argument.method)
        else:
            return argument

    def args(self, obj):
        return [self._transform(arg, obj) for arg in self._args]

    def kwargs(self, obj):
        return {key: self._transform(value, obj) for key, value in self._kwargs.items()}

    def __call__(self, function):
        setattr(function, '__teleapp_function', self)
        return function


class handler:

    _order = 0

    @classmethod
    def get_order(cls):
        try:
            return cls._order
        finally:
            cls._order += 1

    @classmethod
    def message_handler(cls, *args, **kwargs):
        return TeleAppDecorator('message_handler', cls.get_order(), *args, **kwargs)
