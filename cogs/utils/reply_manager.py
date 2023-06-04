import asyncio
from collections.abc import Callable

import discord
from discord.ext import commands

from . import Bot


class DuplicateReplyListenerError(Exception):
    pass


class ReplyManager:
    """See further implementation in /cogs/reply_command.py"""

    DEFAULT_TIMEOUT = 15

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
        timeout: float = DEFAULT_TIMEOUT
    ) -> tuple[commands.SlashContext[Bot], str]:
        if channel in cls.active_listeners:
            raise DuplicateReplyListenerError(repr(channel))

        future: asyncio.Future[
            tuple[commands.SlashContext[Bot], str]
        ] = asyncio.Future()
        cls.active_listeners[channel] = (future, check)

        result = await asyncio.wait_for(future, timeout=timeout)
        cls.active_listeners.pop(channel)
        return result
