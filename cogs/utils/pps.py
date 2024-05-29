import asyncio
import enum
import math
from decimal import Decimal
from typing import Self, Literal

import asyncpg
from discord.ext import commands, vbu

from . import (
    DatabaseWrapperObject,
    DifferenceTracker,
    format_int,
    MEME_URL,
    MarkdownFormat,
    RowLevelLockMode,
    RecordNotFoundError,
    DatabaseTimeoutManager,
    format_slash_command,
    is_weekend,
)


BoostLiteral = Literal["voter", "weekend"]


class BoostType(enum.Enum):
    VOTE = Decimal("3")
    WEEKEND = Decimal(".5")

    @property
    def percentage(self) -> int:
        return int(self.value * 100)


class NoPpCheckFailure(commands.CheckFailure):
    pass


class DatabaseTimeoutCheckFailure(commands.CheckFailure):
    def __init__(self, message: str | None = None, *args, reason: str) -> None:
        super().__init__(message, *args)
        self.reason = reason


class Pp(DatabaseWrapperObject):
    __slots__ = ("user_id", "multiplier", "size", "name", "digging_depth")
    _repr_attributes = __slots__
    _table = "pps"
    _columns = {
        "user_id": "user_id",
        "pp_multiplier": "multiplier",
        "pp_size": "size",
        "pp_name": "name",
        "digging_depth": "digging_depth",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}
    _identifier_attributes = ("user_id",)
    _trackers = ("multiplier", "size", "name", "digging_depth")

    def __init__(
        self, user_id: int, multiplier: int, size: int, name: str, digging_depth: int
    ) -> None:
        self.user_id = user_id
        self.multiplier = DifferenceTracker(multiplier, column="pp_multiplier")
        self.size = DifferenceTracker(size, column="pp_size")
        self.name = DifferenceTracker(name, column="pp_name")
        self.digging_depth = DifferenceTracker(digging_depth, column="digging_depth")

    def get_full_multiplier(
        self, *, voted: bool
    ) -> tuple[int, dict[BoostLiteral, int | Decimal], int | Decimal]:
        """Returns `(full_multiplier: int, boosts: dict[boost: L[...], boost_percentage: int | Decimal], total_boost: int | Decimal)`"""
        boosts: dict[BoostLiteral, int | Decimal] = {}

        multiplier = self.multiplier.value

        if voted:
            boosts["voter"] = BoostType.VOTE.value

        if is_weekend():
            boosts["weekend"] = BoostType.WEEKEND.value

        total_boost = 1
        for multiplier_percentage in boosts.values():
            total_boost += multiplier_percentage

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
            raise NoPpCheckFailure(
                f"You don't have a pp! Go make one with {format_slash_command('new')} and get"
                " started :)"
            )
        except asyncio.TimeoutError:
            raise DatabaseTimeoutCheckFailure(
                DatabaseTimeoutManager.get_notification(user_id),
                reason=DatabaseTimeoutManager.get_reason(user_id),
            )

    async def has_voted(self) -> bool:
        return await vbu.user_has_voted(self.user_id)

    def grow(self, growth: int) -> int:
        self.size.value += growth
        return growth

    def grow_with_multipliers(self, growth: int, *, voted: bool = False) -> int:
        growth *= self.get_full_multiplier(voted=voted)[0]
        self.size.value += growth
        return growth

    def format_growth(
        self,
        growth: int | None = None,
        *,
        markdown: MarkdownFormat | None = MarkdownFormat.BOLD,
        prefixed: bool = False,
    ) -> str:
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
            return prefix + f"{format_int(growth)} inch{'' if growth == 1 else 'es'}"

        if markdown == MarkdownFormat.BOLD:
            return (
                prefix + f"**{format_int(growth)}** inch{'' if growth == 1 else 'es'}"
            )

        return (
            prefix
            + f"**[{format_int(growth)}]({MEME_URL}) inch{'' if growth == 1 else 'es'}**"
        )
