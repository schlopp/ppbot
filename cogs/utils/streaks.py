from datetime import datetime, timedelta, UTC
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
        "last_daily": "last_daily",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}
    _identifier_attributes = ("user_id",)
    _trackers = ("daily", "last_daily")

    def __init__(self, user_id: int, daily: int, last_daily: datetime) -> None:
        self.user_id = user_id
        self.daily = DifferenceTracker(daily, column="daily_streak")
        self.last_daily = DifferenceTracker(last_daily, column="last_daily")

    @property
    def daily_expired(self) -> bool:
        return self.last_daily.value + timedelta(days=2) < datetime.now(UTC).replace(
            tzinfo=None
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
        return await cls.fetch(
            connection,
            {"user_id": user_id},
            lock=RowLevelLockMode.FOR_UPDATE if edit else None,
            timeout=timeout,
            insert_if_not_found=True,
        )
