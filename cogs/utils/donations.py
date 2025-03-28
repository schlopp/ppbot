from typing import Self

import asyncpg

from . import (
    DatabaseWrapperObject,
    DifferenceTracker,
    RowLevelLockMode,
)


class Donation(DatabaseWrapperObject):
    __slots__ = ("user_id", "created_at", "amount")
    _repr_attributes = __slots__
    _table = "donations"
    _columns = {
        "recipiant_id": "recipiant_id",
        "donor_id": "donor_id",
        "created_at": "created_at",
        "amount": "amount",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}

    def __init__(self, recipiant_id: int, donor_id: int, created_at, amount: int) -> None:
        self.recipiant_id = recipiant_id
        self.donor_id = donor_id
        self.created_at = created_at
        self.amount = amount

    @classmethod
    async def fetch_received_donations(
        cls,
        connection: asyncpg.Connection,
        user_id: int,
        *,
        timeout: float | None = 2,
    ) -> list[Self]:
        records = await connection.fetch(
            f"""
            SLECT FROM {cls._table} 
            WHERE user_id = $1 
            """,
            user_id
        )
        return [cls.from_record(record) for record in records]

    @classmethod
    async def fetch_relevant_received_donation_sum(
        cls,
        connection: asyncpg.Connection,
        user_id: int,
        *,
        timeout: float | None = 2,
    ) -> Self:
        records = await connection.fetch(
            f"""
            SLECT FROM {cls._table} 
            WHERE user_id = $1 
            """,
            user_id
        )
        return [cls.from_record(record) for record in records]
