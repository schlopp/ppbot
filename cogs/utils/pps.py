from collections.abc import Mapping
from typing import Any

import asyncpg  # type: ignore

from . import Object, DifferenceTracker


class PpRecordNotFoundError(Exception):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self.message = (
            f"Database record for pp with the user ID of {self.user_id!r} not found"
        )


class Pp(Object):
    __slots__ = ("user_id", "multiplier", "size", "name")
    _repr_attributes = __slots__

    def __init__(self, user_id: int, multiplier: int, size: int, name: str) -> None:
        self.user_id = user_id
        self.multiplier = DifferenceTracker(multiplier, column="pp_multiplier")
        self.size = DifferenceTracker(size, column="pp_size")
        self.name = DifferenceTracker(name, column="pp_name")

    @classmethod
    async def fetch(
        cls,
        user_id: int,
        connection: asyncpg.Connection,
        *,
        lock_for_update: bool = False,
    ):
        query = "SELECT * FROM pps WHERE user_id = $1"
        if lock_for_update:
            query += " FOR UPDATE"
        record: list[Mapping[str, Any]] = await connection.fetchrow(
            "SELECT * FROM pps WHERE user_id = $1 FOR UPDATE", user_id
        )
        if record is None:
            raise PpRecordNotFoundError(user_id)
        return cls(
            record["user_id"],
            record["pp_multiplier"],
            record["pp_size"],
            record["pp_name"],
        )
