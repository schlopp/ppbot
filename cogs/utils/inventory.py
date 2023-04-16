from __future__ import annotations
import asyncpg

from . import DatabaseWrapperObject, DifferenceTracker


class InventoryItem(DatabaseWrapperObject):
    __slots__ = ("user_id", "id", "amount")
    _repr_attributes = __slots__
    _table = "inventory"
    _columns = {
        "user_id": "user_id",
        "item_id": "id",
        "item_amount": "amount",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}
    _identifier_attributes = ("user_id", "id")
    _trackers = ("amount",)

    def __init__(self, user_id: int, id: str, amount: int) -> None:
        self.user_id = user_id
        self.id = id
        self.amount = DifferenceTracker(amount, column="item_amount")

    async def update(
        self, connection: asyncpg.Connection, ensure_difference: bool = True
    ):
        if ensure_difference and self.amount.difference is None:
            return
        if not self.amount.value:
            await connection.execute(
                "DELETE FROM inventory WHERE user_id=$1 AND item_id=$2",
                self.user_id,
                self.id,
            )
            return
        await connection.execute(
            """
            INSERT INTO inventory
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, item_id)
            DO UPDATE SET item_amount=$3
            """,
            self.user_id,
            self.id,
            self.amount.value,
        )

    @staticmethod
    async def has_item(connection: asyncpg.Connection, user_id: int, id: str) -> bool:
        return bool(
            await connection.fetchval(
                """
            SELECT 1
            FROM inventory
            WHERE
                user_id = $1
                AND item_id = $2
                AND item_amount >= 1
            """,
                user_id,
                id,
            )
        )
