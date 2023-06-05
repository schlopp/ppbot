from __future__ import annotations
import asyncio
from collections.abc import Callable

import discord
from discord.ext import commands

from . import Bot, Object


class DuplicateReplyListenerError(Exception):
    pass


class ReplyManager:
    """See further implementation in /cogs/reply_command.py"""

    DEFAULT_TIMEOUT = 30

    active_listeners: dict[
        discord.TextChannel,
        tuple[
            asyncio.Future[tuple[commands.SlashContext[Bot], str]],
            Callable[[commands.SlashContext[Bot], str], bool],
        ],
    ] = {}

    @classmethod
    async def wait_for_reply(
        cls,
        channel: discord.TextChannel,
        *,
        check: Callable[[commands.SlashContext[Bot], str], bool] = lambda _, _1: True,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> tuple[commands.SlashContext[Bot], str]:
        if channel in cls.active_listeners:
            raise DuplicateReplyListenerError(repr(channel))

        future: asyncio.Future[
            tuple[commands.SlashContext[Bot], str]
        ] = asyncio.Future()
        cls.active_listeners[channel] = (future, check)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        finally:
            cls.active_listeners.pop(channel)


class DatabaseTimeoutManager:
    DEFAULT_NOTIFICATION = "You're busy doing something else right now!"
    NOTIFICATIONS: dict[int, list[str]] = {}

    @classmethod
    def get_notification(cls, user_id: int) -> str:
        try:
            notification = cls.NOTIFICATIONS.get(user_id, cls.DEFAULT_NOTIFICATION)[0]
        except (KeyError, IndexError):
            notification = cls.DEFAULT_NOTIFICATION
        return f"{notification} Try again later."

    @classmethod
    def add_notification(cls, user_id: int, notification: str) -> None:
        try:
            cls.NOTIFICATIONS[user_id].append(notification)
        except KeyError:
            cls.NOTIFICATIONS[user_id] = [notification]

    @classmethod
    def clear_notification(cls, user_id: int) -> None:
        try:
            cls.NOTIFICATIONS[user_id].pop(0)
        except KeyError:
            pass

    @classmethod
    def notify(cls, user_id: int, notification: str) -> NotificationContextManager:
        return NotificationContextManager(user_id, notification)


class NotificationContextManager(Object):
    __slots__ = ("user_id", "notification")
    _repr_attributes = __slots__

    def __init__(self, user_id: int, notification: str) -> None:
        self.user_id = user_id
        self.notification = notification

    def __enter__(self) -> None:
        DatabaseTimeoutManager.add_notification(self.user_id, self.notification)

    def __exit__(self, *_):
        DatabaseTimeoutManager.clear_notification(self.user_id)

    async def __aenter__(self) -> None:
        return self.__enter__()

    async def __aexit__(self, *_) -> None:
        return self.__exit__()
