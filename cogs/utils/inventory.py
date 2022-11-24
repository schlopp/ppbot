from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from typing_extensions import Protocol


import asyncpg  # type: ignore

from . import DatabaseWrapperObject, DifferenceTracker, Record


class _SupportsGetItem(Protocol):
    def __getitem__(self, index):
        ...


async def fetch_inventory(
    user_id: int,
    connection: asyncpg.Connection,
    *,
    items: list[str] | None = None,
    lock_for_update: bool = False,
) -> dict[str, int]:
    args = [user_id]
    query = "SELECT item_name, amount FROM inventory WHERE user_id = $1"

    if items is not None:
        query = "+= AND item_name IN $2"
        args.append(items)

    if lock_for_update:
        query += " FOR UPDATE"

    rows = await connection.fetch(query, *args)
    return {record["item_name"]: record["amount"] for record in rows}


async def fetch_inventory_item_amount(
    user_id: int,
    item_name: str,
    connection: asyncpg.Connection,
    *,
    lock_for_update: bool = False,
) -> int:
    query = "SELECT amount FROM inventory WHERE user_id = $1 AND item_name = $2"
    if lock_for_update:
        query += " FOR UPDATE"
    amount = await connection.fetchval(query, user_id, item_name)
    return 0 if amount is None else amount


class InventoryItem(DatabaseWrapperObject):
    __slots__ = ("user_id", "name", "amount")
    _repr_attributes = __slots__
    _table = "inventory"
    _columns = {
        "user_id": "user_id",
        "item_name": "name",
        "item_amount": "amount",
    }
    _column_attributes = dict(map(reversed, _columns.items()))
    _identifier_attributes = ("user_id", "name")
    _trackers = ("amount",)

    def __init__(self, user_id: int, name: str, amount: int) -> None:
        self.user_id = user_id
        self.name = name
        self.amount = DifferenceTracker(amount, column="item_amount")

    @classmethod
    async def fetch_all(
        cls, connection: asyncpg.Connection, user_id: int
    ) -> list[InventoryItem]:
        records: list[Record] = connection.fetch(
            "SELECT * FROM inventory WHERE user_id = $1", user_id
        )
        return [cls.from_record(record) for record in records]

    async def update(
        self, connection: asyncpg.Connection, ensure_difference: bool = True
    ):
        if ensure_difference and self.amount.difference is None:
            return
        if not self.amount.value:
            await connection.execute(
                "DELETE FROM inventory WHERE user_id=$1 AND item_name=$2",
                self.user_id,
                self.name,
            )
            return
        await connection.execute(
            """
            INSERT INTO inventory
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, item_name)
            DO UPDATE SET item_amount=$3
            """,
            self.user_id,
            self.name,
            self.amount.value,
        )
