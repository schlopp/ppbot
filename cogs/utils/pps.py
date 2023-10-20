import asyncio
from typing import Self

import asyncpg
from discord.ext import commands

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
)


class NoPpCheckFailure(commands.CheckFailure):
    pass


class Pp(DatabaseWrapperObject):
    __slots__ = ("user_id", "multiplier", "size", "name")
    _repr_attributes = __slots__
    _table = "pps"
    _columns = {
        "user_id": "user_id",
        "pp_multiplier": "multiplier",
        "pp_size": "size",
        "pp_name": "name",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}
    _identifier_attributes = ("user_id",)
    _trackers = ("multiplier", "size", "name")

    def __init__(self, user_id: int, multiplier: int, size: int, name: str) -> None:
        self.user_id = user_id
        self.multiplier = DifferenceTracker(multiplier, column="pp_multiplier")
        self.size = DifferenceTracker(size, column="pp_size")
        self.name = DifferenceTracker(name, column="pp_name")

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
            raise commands.CheckFailure(
                DatabaseTimeoutManager.get_notification(user_id)
            )

    def grow(self, growth: int, *, include_multipliers: bool = True) -> int:
        if include_multipliers:
            growth *= self.multiplier.value
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
