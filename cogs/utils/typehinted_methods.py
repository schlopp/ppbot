import asyncpg  # type: ignore
from discord.ext import vbu


def get_database_connection(db: vbu.DatabaseConnection) -> asyncpg.Connection:
    return db.conn
