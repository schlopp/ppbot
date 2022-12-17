from __future__ import annotations
from typing import cast


from discord.ext import vbu
import asyncpg  # type: ignore


class DatabaseWrapper(vbu.DatabaseWrapper):
    conn: asyncpg.Connection

    async def __aenter__(self) -> DatabaseWrapper:
        return cast(DatabaseWrapper, await super().__aenter__())


class Bot(vbu.Bot):
    database: type[DatabaseWrapper]
