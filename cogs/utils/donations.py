from datetime import datetime
from typing import Self

import asyncpg

from . import (
    DatabaseWrapperObject,
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

    def __init__(
        self, recipiant_id: int, donor_id: int, created_at: datetime, amount: int
    ) -> None:
        self.recipiant_id = recipiant_id
        self.donor_id = donor_id
        self.created_at = created_at
        self.amount = amount

    @classmethod
    async def register(
        cls,
        connection: asyncpg.Connection,
        recipiant_id: int,
        donor_id: int,
        amount: int,
    ) -> None:
        await connection.execute(
            """
            INSERT INTO donations (recipiant_id, donor_id, amount)
            VALUES ($1, $2, $3)
            """,
            recipiant_id,
            donor_id,
            amount,
        )

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
            SELECT *
            FROM {cls._table}
            WHERE recipiant_id = $1
            """,
            user_id,
            timeout=timeout,
        )
        return [cls.from_record(record) for record in records]

    @classmethod
    async def fetch_relevant_received_donation_sum(
        cls,
        connection: asyncpg.Connection,
        user_id: int,
        *,
        timeout: float | None = 2,
    ) -> int:
        record = await connection.fetchrow(
            f"""
            SELECT sum(amount) AS total_amount
            FROM {cls._table}
            WHERE recipiant_id = $1
            """,
            user_id,
            timeout=timeout,
        )

        if record is None or record["total_amount"] is None:
            return 0

        return record["total_amount"]
