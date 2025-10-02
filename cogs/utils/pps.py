import asyncio
import enum
import math
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from typing import Self, Literal

import asyncpg
import discord
from discord.ext import commands, vbu

from . import (
    InteractionChannel,
    DatabaseWrapperObject,
    DifferenceTracker,
    format_int,
    MEME_URL,
    VOTE_URL,
    MarkdownFormat,
    RowLevelLockMode,
    RecordNotFoundError,
    DatabaseTimeoutManager,
    format_slash_command,
    is_weekend,
    PpMissing,
)


NEW_UPDATE_EVENT_LIVE = True


class BoostType(enum.Enum):
    VOTER = (Decimal("3"), "voter", f"for voting on [**top.gg**]({VOTE_URL})")
    NEW_UPDATE_EVENT = (Decimal("3"), "NEW UPDATE", "from the **NEW UPDATE EVENT**")
    WEEKEND = (Decimal(".5"), "weekend", "for playing during the weekend :)")
    PP_BOT_CHANNEL = (
        Decimal(".10"),
        "#pp-bot",
        "for being in a channel named after pp bot <:ppHappy:902894208703156257>",
    )

    @property
    def percentage(self) -> int:
        return int(self.value[0] * 100)


class DatabaseTimeout(commands.CheckFailure):
    def __init__(
        self,
        message: str | None = None,
        *args,
        reason: str,
        casino_id: str | None = None,
    ) -> None:
        super().__init__(message, *args)
        self.reason = reason
        self.casino_id = casino_id


class Pp(DatabaseWrapperObject):
    __slots__ = ("user_id", "multiplier", "size", "name", "digging_depth", "created_at")
    _repr_attributes = __slots__
    _table = "pps"
    _columns = {
        "user_id": "user_id",
        "pp_multiplier": "multiplier",
        "pp_size": "size",
        "pp_name": "name",
        "digging_depth": "digging_depth",
        "created_at": "created_at",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}
    _identifier_attributes = ("user_id",)
    _trackers = ("multiplier", "size", "name", "digging_depth")

    def __init__(
        self,
        user_id: int,
        multiplier: int,
        size: int,
        name: str,
        digging_depth: int,
        created_at: datetime,
    ) -> None:
        self.user_id = user_id
        self.multiplier = DifferenceTracker(multiplier, column="pp_multiplier")
        self.size = DifferenceTracker(size, column="pp_size")
        self.name = DifferenceTracker(name, column="pp_name")
        self.digging_depth = DifferenceTracker(digging_depth, column="digging_depth")
        self.created_at = created_at

    @property
    def age(self) -> timedelta:
        return datetime.now(UTC).replace(tzinfo=None) - self.created_at

    def get_full_multiplier(
        self,
        *,
        voted: bool,
        channel: str | InteractionChannel | None,
    ) -> tuple[int, list[BoostType], int | Decimal]:
        """Returns `(full_multiplier: int, boosts: list[BoostType], total_boost: int | Decimal)`"""
        boosts: list[BoostType] = []

        multiplier = self.multiplier.value

        if voted:
            boosts.append(BoostType.VOTER)

        channel_name = None
        if channel is not None:
            if not isinstance(channel, str):
                channel_name = getattr(channel, "name", None)
            if not isinstance(channel_name, str):  # accounting for getattr giving Any
                channel_name = None

        if NEW_UPDATE_EVENT_LIVE:
            boosts.append(BoostType.NEW_UPDATE_EVENT)

        if is_weekend():
            boosts.append(BoostType.WEEKEND)

        if channel_name is not None and (
            "pp-bot" in channel_name or "ppbot" in channel_name
        ):
            boosts.append(BoostType.PP_BOT_CHANNEL)

        total_boost = 1
        for boost in boosts:
            total_boost += boost.value[0]

        return math.ceil(multiplier * total_boost), boosts, total_boost

    @classmethod
    async def fetch_from_user(
        cls,
        connection: asyncpg.Connection,
        user_id: int,
        *,
        edit: bool = False,
        timeout: float | None = 2,
    ) -> Self:
        try:
            return await cls.fetch(
                connection,
                {"user_id": user_id},
                lock=RowLevelLockMode.FOR_UPDATE if edit else None,
                timeout=timeout,
            )
        except RecordNotFoundError:
            raise PpMissing(
                f"You don't have a pp! Go make one with {format_slash_command('new')} and get"
                " started :)"
            )
        except asyncio.TimeoutError:
            reason, casino_id = DatabaseTimeoutManager.get_reason(user_id)
            raise DatabaseTimeout(
                DatabaseTimeoutManager.get_notification(user_id)[0],
                reason=reason,
                casino_id=casino_id,
            )

    async def has_voted(self) -> bool:
        return await vbu.user_has_voted(self.user_id)

    def grow(self, growth: int) -> int:
        self.size.value += growth
        return growth

    def grow_with_multipliers(
        self,
        growth: int,
        *,
        voted: bool,
        channel: str | InteractionChannel | None,
    ) -> int:
        growth *= self.get_full_multiplier(voted=voted, channel=channel)[0]
        self.size.value += growth
        return growth

    def format_growth(
        self,
        growth: int | None = None,
        *,
        markdown: MarkdownFormat | None = MarkdownFormat.BOLD,
        prefixed: bool = False,
        in_between: str | None = None,
    ) -> str:
        if in_between is None:
            in_between = ""

        if growth is None:
            growth = self.size.difference or 0

        if prefixed:
            if growth < 0:
                prefix = "lost "
                growth = abs(growth)
            else:
                prefix = "earned "
        else:
            prefix = ""

        if markdown is None:
            return (
                prefix
                + f"{format_int(growth)}{in_between} inch{'' if growth == 1 else 'es'}"
            )

        if markdown == MarkdownFormat.BOLD:
            return (
                prefix
                + f"**{format_int(growth)}**{in_between} inch{'' if growth == 1 else 'es'}"
            )

        return (
            prefix
            + f"**[{format_int(growth)}]({MEME_URL}){in_between} inch{'' if growth == 1 else 'es'}**"
        )


class PpExtras(DatabaseWrapperObject):
    __slots__ = ("user_id", "is_og")
    _repr_attributes = __slots__
    _table = "pp_extras"
    _columns = {
        "user_id": "user_id",
        "is_og": "is_og",
        "last_played_version": "last_played_version",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}
    _identifier_attributes = ("user_id",)
    _trackers = ("is_og", "last_played_version")

    def __init__(
        self,
        user_id: int,
        is_og: bool,
        last_played_version: str | None,
    ) -> None:
        self.user_id = user_id
        self.is_og = DifferenceTracker(is_og, column="is_og")
        self.last_played_version = DifferenceTracker(
            last_played_version, column="last_played_version"
        )

    @classmethod
    async def fetch_from_user(
        cls,
        connection: asyncpg.Connection,
        user_id: int,
        *,
        edit: bool = False,
        timeout: float | None = 2,
    ) -> Self:
        try:
            return await cls.fetch(
                connection,
                {"user_id": user_id},
                lock=RowLevelLockMode.FOR_UPDATE if edit else None,
                timeout=timeout,
                insert_if_not_found=True,
            )
        except asyncio.TimeoutError:
            reason, casino_id = DatabaseTimeoutManager.get_reason(user_id)
            raise DatabaseTimeout(
                DatabaseTimeoutManager.get_notification(user_id)[0],
                reason=reason,
                casino_id=casino_id,
            )
