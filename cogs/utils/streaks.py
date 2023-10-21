from typing import Self

import asyncpg

from . import (
    DatabaseWrapperObject,
    DifferenceTracker,
    RowLevelLockMode,
)


class Streaks(DatabaseWrapperObject):
    __slots__ = ("user_id", "daily")
    _repr_attributes = __slots__
    _table = "streaks"
    _columns = {
        "user_id": "user_id",
        "daily_streak": "daily",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}
    _identifier_attributes = ("user_id",)
    _trackers = ("daily",)

    def __init__(self, user_id: int, daily: int) -> None:
        self.user_id = user_id
        self.daily = DifferenceTracker(daily, column="daily_streak")

    @classmethod
    async def fetch_from_user(
        cls,
        connection: asyncpg.Connection,
        user_id: int,
        *,
        edit: bool = False,
        timeout: float | None = 2,
    ) -> Self:
        return await cls.fetch(
            connection,
            {"user_id": user_id},
            lock=RowLevelLockMode.FOR_UPDATE if edit else None,
            timeout=timeout,
            insert_if_not_found=True,
        )
