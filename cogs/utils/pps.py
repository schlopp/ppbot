from collections.abc import Mapping
from typing import Any

import asyncpg  # type: ignore

from . import DatabaseWrapperObject, DifferenceTracker, Record


class PpRecordNotFoundError(Exception):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self.message = (
            f"Database record for pp with the user ID of {self.user_id!r} not found"
        )


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
    _column_attributes = dict(map(reversed, _columns.items()))
    _identifier_attributes = ("user_id",)
    _trackers = ("multiplier", "size", "name")

    def __init__(self, user_id: int, multiplier: int, size: int, name: str) -> None:
        self.user_id = user_id
        self.multiplier = DifferenceTracker(multiplier, column="pp_multiplier")
        self.size = DifferenceTracker(size, column="pp_size")
        self.name = DifferenceTracker(name, column="pp_name")
