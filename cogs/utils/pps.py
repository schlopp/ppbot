from collections.abc import Mapping
from typing import Any

import asyncpg  # type: ignore

from . import DatabaseWrapperObject, DifferenceTracker


class PpRecordNotFoundError(Exception):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self.message = (
            f"Database record for pp with the user ID of {self.user_id!r} not found"
        )


class Pp(DatabaseWrapperObject):
    __slots__ = ("user_id", "multiplier", "size", "name")
    _repr_attributes = __slots__
    _trackers = ("multiplier", "size", "name")
    _table = "pps"

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
            return None
        return cls(
            record["user_id"],
            record["pp_multiplier"],
            record["pp_size"],
            record["pp_name"],
        )

    async def update(self, connection: asyncpg.Connection):
        generated_query = self._generate_pgsql_set_query(2)
        if generated_query is None:
            return
        set_query, set_args = generated_query
        query = f"UPDATE pps {set_query} WHERE user_id = $1"
        await connection.execute(query, self.user_id, *set_args)
