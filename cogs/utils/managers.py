from __future__ import annotations
import asyncio
import random
from collections.abc import Callable

import discord
from discord.ext import commands

from . import MEME_URL, Bot, Object


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
        check: Callable[
            [commands.SlashContext[Bot], str], bool
        ] = lambda ctx, reply: True,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> tuple[commands.SlashContext[Bot], str]:
        """Returns `(ctx: commands.SlashContext[Bot], reply: str)`"""
        if channel in cls.active_listeners:
            raise DuplicateReplyListenerError(repr(channel))

        future: asyncio.Future[tuple[commands.SlashContext[Bot], str]] = (
            asyncio.Future()
        )
        cls.active_listeners[channel] = (future, check)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        finally:
            cls.active_listeners.pop(channel)


class DatabaseTimeoutManager:
    DEFAULT_REASON = ("You're busy doing something else right now!", None)
    REASONS: dict[int, list[tuple[str, str | None]]] = {}

    @classmethod
    def get_reason(cls, user_id: int) -> tuple[str, str | None]:
        try:
            return cls.REASONS.get(user_id, [cls.DEFAULT_REASON])[0]
        except IndexError:
            return cls.DEFAULT_REASON

    @classmethod
    def get_notification(cls, user_id: int) -> tuple[str, str | None]:
        reason, casino_id = cls.get_reason(user_id)
        return f"{reason} Try again later.", casino_id

    @classmethod
    def add_notification(
        cls, user_id: int, notification: str, casino_id: str | None = None
    ) -> None:
        try:
            cls.REASONS[user_id].append((notification, casino_id))
        except KeyError:
            cls.REASONS[user_id] = [(notification, casino_id)]

    @classmethod
    def clear_notification(cls, user_id: int, *, index: int = 0) -> None:
        try:
            cls.REASONS[user_id].pop(index)
        except KeyError:
            pass

    @classmethod
    def notify(
        cls, user_id: int, notification: str, casino_id: str | None = None
    ) -> NotificationContextManager:
        return NotificationContextManager(user_id, notification, casino_id=casino_id)


class NotificationContextManager(Object):
    __slots__ = ("user_id", "notification")
    _repr_attributes = __slots__

    def __init__(
        self, user_id: int, notification: str, *, casino_id: str | None = None
    ) -> None:
        self.user_id = user_id
        self.notification = notification
        self.casino_id = casino_id

    def __enter__(self) -> None:
        DatabaseTimeoutManager.add_notification(
            self.user_id, self.notification, casino_id=self.casino_id
        )

    def __exit__(self, exc_type: type[BaseException] | None, *_):
        if exc_type is None or not issubclass(exc_type, commands.CheckFailure):
            DatabaseTimeoutManager.clear_notification(self.user_id)
            return
        DatabaseTimeoutManager.clear_notification(self.user_id, index=-1)

    async def __aenter__(self) -> None:
        return self.__enter__()

    async def __aexit__(self, *args, **kwargs) -> None:
        return self.__exit__(*args, **kwargs)


async def wait_for_component_interaction(
    bot: Bot,
    interaction_id: str,
    *,
    users: list[discord.User | discord.Member] | None = None,
    actions: list[str] | None = None,
    timeout: float | None = 30,
) -> tuple[discord.ComponentInteraction, str]:
    """Returns `(component_interaction: commands.ComponentInteraction, action: str)`"""

    def component_interaction_check(
        component_interaction: discord.ComponentInteraction,
    ) -> bool:
        try:
            found_interaction_id, found_action = component_interaction.custom_id.split(
                "_", 1
            )
        except ValueError:
            return False

        if found_interaction_id != interaction_id:
            return False

        if users and component_interaction.user not in users:
            asyncio.create_task(
                component_interaction.response.send_message(
                    random.choice(
                        [
                            "This button ain't for you lil bra.",
                            "Don't click no random ahh buttons that aren't meant for you",
                            "You not supposed to click that button gang",
                            (
                                "You got a rare reward reward for clicking random buttons!!!"
                                f" Claim it **[here!!!!!](<{MEME_URL}>)**"
                            ),
                        ]
                    ),
                    ephemeral=True,
                )
            )
            return False

        if actions and found_action not in actions:
            return False

        return True

    component_interaction = await bot.wait_for(
        "component_interaction",
        check=component_interaction_check,
        timeout=timeout,
    )

    found_action = component_interaction.custom_id.split("_", 1)[1]
    return component_interaction, found_action


class SlashCommandMappingManager:
    slash_command_ids: dict[str, int] = {}

    @classmethod
    async def load(cls, bot: Bot) -> None:
        app_commands = await bot.fetch_global_application_commands()
        cls.slash_command_ids.clear()

        for app_command in app_commands:
            if app_command.type != discord.ApplicationCommandType.chat_input:
                continue

            assert app_command.id is not None
            cls.slash_command_ids[app_command.name] = app_command.id

    @classmethod
    def format_slash_command(cls, command_name: str) -> str:
        command_base = command_name.split()[0]

        try:
            return f"</{command_name}:{cls.slash_command_ids[command_base]}>"
        except KeyError:
            return f"/{command_name}"


def format_slash_command(command_name: str) -> str:
    return SlashCommandMappingManager.format_slash_command(command_name)
