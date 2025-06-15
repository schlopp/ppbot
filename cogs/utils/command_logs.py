from datetime import datetime

import asyncpg

from . import (
    DatabaseWrapperObject,
    DifferenceTracker,
)


class CommandLog(DatabaseWrapperObject):
    __slots__ = ("command_name", "timeframe", "usage")
    _repr_attributes = __slots__
    _table = "command_logs"
    _columns = {
        "command_name": "command_name",
        "timeframe": "timeframe",
        "usage": "usage",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}
    _identifier_attributes = ("command_name", "timeframe")
    _trackers = ("usage",)

    def __init__(self, command_name: str, timeframe: datetime, usage: int) -> None:
        self.command_name = command_name
        self.timeframe = timeframe
        self.usage = DifferenceTracker(usage, column="usage")

    @classmethod
    async def increment(cls, connection: asyncpg.Connection, command_name: str) -> None:
        await connection.execute(
            f"""
            INSERT INTO {cls._table} (command_name, usage)
            VALUES ($1, 1)
            ON CONFLICT (command_name, timeframe)
            DO UPDATE SET usage = {cls._table}.usage + 1
            """,
            command_name,
        )
