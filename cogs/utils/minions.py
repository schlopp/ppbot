from __future__ import annotations
import asyncpg
import logging
import re
from datetime import timedelta
from functools import cached_property
from typing import Any, Literal, Self
from string import ascii_letters, digits

import toml
import rust_utils  # pyright: ignore[reportMissingModuleSource]
from discord.ext import commands

from . import (
    Object,
    DatabaseWrapperObject,
    DifferenceTracker,
    MarkdownFormat,
    format_slash_command,
    format_roman,
    ItemManager,
    Item,
)

MinionPerkLiterals = Literal["BONUS"]


class UnknownMinionError(Exception):
    pass


class MinionEmojis(Object):
    __slots__ = ("tl", "tr", "bl", "br")
    _repr_attributes = __slots__

    def __init__(self, tl: str, tr: str, bl: str, br: str) -> None:
        self.tl = tl
        self.tr = tr
        self.bl = bl
        self.br = br


class MinionLevel(Object):
    __slots__ = ("level", "percent", "duration", "required_items")
    _repr_attributes = __slots__

    def __init__(
        self,
        level: int,
        percent: int,
        duration: timedelta,
        required_items: dict[Item, int],
    ) -> None:
        if level > 10:
            raise ValueError(f"Expected level <= 10, received level > 10 ({level})")
        self.level = level
        self.percent = percent
        self.duration = duration
        self.required_items = required_items


class Minion(Object):
    __slots__ = (
        "id",
        "name",
        "quote",
        "base_inches_per_minute",
        "perk",
        "emojis",
        "levels",
    )
    _repr_attributes = __slots__

    def __init__(
        self,
        id: str,
        *,
        name: str,
        quote: str,
        base_inches_per_minute: int,
        perk: MinionPerkLiterals,
        emojis: MinionEmojis,
        levels: list[MinionLevel],
    ) -> None:
        self.id = id
        self.name = name
        self.quote = quote
        self.base_inches_per_minute = base_inches_per_minute
        self.perk = perk
        self.emojis = emojis
        self.levels = levels

    def format_minion(self, level: int) -> str:
        return f"[LVL {format_roman(level)}] {self.name}"

    def get_level(self, level: int) -> MinionLevel:
        return self.levels[level - 1]


class OwnedMinion(DatabaseWrapperObject):
    __slots__ = ("user_id", "id", "level")
    _repr_attributes = __slots__ + ("minion",)
    _table = "minions"
    _columns = {
        "user_id": "user_id",
        "minion_id": "id",
        "minion_level": "level",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}
    _identifier_attributes = ("user_id", "id")
    _trackers = ("level",)

    def __init__(self, user_id: int, id: str, level: int) -> None:
        self.user_id = user_id
        self.id = id
        self.level = DifferenceTracker(level, column="minion_level")

    @cached_property
    def minion(self) -> Minion:
        return MinionManager.get(self.id)

    @property
    def inches_per_minute(self) -> int:
        return self.minion.base_inches_per_minute * self.level.value

    @property
    def capacity(self) -> int:
        fill_time_per_level: dict[int, timedelta] = {
            1: timedelta(minutes=30),
            2: timedelta(hours=1),
            3: timedelta(hours=2),
            4: timedelta(hours=4),
            5: timedelta(hours=8),
            6: timedelta(days=1),
            7: timedelta(days=2),
            8: timedelta(days=4),
            9: timedelta(days=7),
            10: timedelta(days=14),
        }
        return (
            int(fill_time_per_level[self.level.value].total_seconds() / 60)
            * self.inches_per_minute
        )

    def format_minion(
        self,
    ) -> str:
        return self.minion.format_minion(self.level.value)

    async def update(
        self,
        connection: asyncpg.Connection,
        *,
        ensure_difference: bool = True,
    ):
        if ensure_difference and self.level.difference is None:
            return

        if not self.level.value:
            await connection.execute(
                "DELETE FROM minions WHERE user_id=$1 AND minion_id=$2",
                self.user_id,
                self.id,
            )
            return

        await connection.execute(
            f"""
            INSERT INTO minions
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, minion_id)
            DO UPDATE SET minion_level=$3
            """,
            self.user_id,
            self.id,
            self.level.value,
        )

    @staticmethod
    async def user_has_minion(
        connection: asyncpg.Connection, user_id: int, *minion_ids: str, any: bool = True
    ) -> bool:
        if not minion_ids:
            raise ValueError("No item ID(s) given")

        if any:
            return bool(
                await connection.fetchval(
                    f"""
                    SELECT 1
                    FROM minions
                    WHERE
                        user_id = $1
                        AND minion_id IN ({", ".join(f"${n + 2}" for n in range(len(minion_ids)))})
                        AND minion_level > 0
                    """,
                    user_id,
                    *minion_ids,
                )
            )
        for minion_id in minion_ids:
            if await connection.fetchval(
                f"""
                SELECT 1
                FROM minions
                WHERE
                    user_id = $1
                    AND minion_id = $2
                    AND minion_level > 0
                """,
                user_id,
                minion_id,
            ):
                return True

        return False


class MinionManager:
    minions: dict[str, Minion] = {}
    _logger = logging.getLogger("vbu.bot.cog.utils.MinionManager")

    # ---------------------------------------------------------------- get

    @classmethod
    def get(cls, minion_id: str) -> Minion:
        try:
            return cls.minions[minion_id]
        except KeyError:
            raise UnknownMinionError(repr(minion_id)) from None

    # ---------------------------------------------------------------- add / remove

    @classmethod
    def add(cls, *minions: Minion) -> None:
        for minion in minions:
            cls.minions[minion.id] = minion

    @classmethod
    def remove(cls, minion_id: str) -> None:
        try:
            cls.minions.pop(minion_id)
        except KeyError:
            raise UnknownMinionError(repr(minion_id)) from None

    # ---------------------------------------------------------------- load

    @classmethod
    def load(cls) -> None:
        data: dict[str, dict[str, dict[str, Any]]] = toml.load("config/minions.toml")

        new_minions: list[Minion] = []
        for minion_id, minion_data in data["minions"].items():
            new_minion = cls._build_minion(minion_id, minion_data)
            new_minions.append(new_minion)
            cls._logger.info(f" * Loaded minion {new_minion.id!r}")

        # swap atomically: no window where the registry is empty
        cls.minions.clear()
        cls.add(*new_minions)

    # ---------------------------------------------------------------- building

    @classmethod
    def _build_minion(cls, minion_id: str, data: dict[str, Any]) -> Minion:
        emoji_data = data["emojis"]

        return Minion(
            minion_id,
            name=data["name"],
            quote=data["quote"],
            base_inches_per_minute=data["base_inches_per_minute"],
            perk=data["perk"],
            emojis=MinionEmojis(
                tl=emoji_data["tl"],
                tr=emoji_data["tr"],
                bl=emoji_data["bl"],
                br=emoji_data["br"],
            ),
            levels=[
                MinionLevel(
                    level=index,
                    percent=level_data["percent"],
                    duration=timedelta(minutes=level_data["duration_min"]),
                    required_items={
                        ItemManager.get(item_key): count
                        for item_key, count in level_data["required_items"].items()
                    },
                )
                for index, level_data in enumerate(data["levels"], start=1)
            ],
        )
