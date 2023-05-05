from __future__ import annotations
import asyncpg
from datetime import timedelta
from typing import Any

import toml

from . import Object, DatabaseWrapperObject, DifferenceTracker


class UnknownItemError(Exception):
    pass


class UselessItem(Object):
    __slots__ = ("id", "name", "description")
    _repr_attributes = __slots__

    def __init__(self, id: str, *, name: str, description: str, price: int) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.price = price


class MultiplierItem(UselessItem):
    __slots__ = ("id", "name", "description", "gain")
    _repr_attributes = __slots__

    def __init__(
        self, id: str, *, name: str, description: str, price: int, gain: int
    ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.gain = gain


class BuffItem(UselessItem):
    __slots__ = (
        "id",
        "name",
        "description",
        "multiplier",
        "duration",
        "cooldown",
        "specified_perks",
    )
    _repr_attributes = __slots__

    def __init__(
        self,
        id: str,
        *,
        name: str,
        description: str,
        price: int,
        duration: timedelta,
        cooldown: str | None,
        multiplier: int | None,
        specified_perks: list[str] | None,
    ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.multiplier = multiplier
        self.duration = duration
        self.cooldown = cooldown
        self.specified_perks = specified_perks


class ToolItem(UselessItem):
    __slots__ = ("id", "name", "description", "price", "associated_command_name")
    _repr_attributes = __slots__

    def __init__(
        self,
        id: str,
        *,
        name: str,
        description: str,
        price: int,
        associated_command_name: str,
    ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.associated_command_name = associated_command_name


Item = UselessItem | MultiplierItem | BuffItem | ToolItem


class InventoryItem(DatabaseWrapperObject):
    __slots__ = ("user_id", "id", "amount")
    _repr_attributes = __slots__ + ("item",)
    _table = "inventories"
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

    @property
    def item(self) -> Item:
        return ItemManager.get(self.id)

    async def update(
        self, connection: asyncpg.Connection, ensure_difference: bool = True
    ):
        if ensure_difference and self.amount.difference is None:
            return
        if not self.amount.value:
            await connection.execute(
                "DELETE FROM inventories WHERE user_id=$1 AND item_id=$2",
                self.user_id,
                self.id,
            )
            return
        await connection.execute(
            """
            INSERT INTO inventories
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, item_id)
            DO UPDATE SET item_amount=$3
            """,
            self.user_id,
            self.id,
            self.amount.value,
        )

    @staticmethod
    async def user_has_item(
        connection: asyncpg.Connection, user_id: int, item_id: str
    ) -> bool:
        return bool(
            await connection.fetchval(
                """
            SELECT 1
            FROM inventories
            WHERE
                user_id = $1
                AND item_id = $2
                AND item_amount >= 1
            """,
                user_id,
                item_id,
            )
        )


class ItemManager:
    items: dict[str, Item] = {}
    multipliers: dict[str, MultiplierItem] = {}
    buffs: dict[str, BuffItem] = {}
    tools: dict[str, ToolItem] = {}
    useless: dict[str, UselessItem] = {}

    @classmethod
    def get(cls, item_id: str) -> Item:
        try:
            return cls.items[item_id]
        except KeyError:
            raise UnknownItemError(repr(item_id))

    @classmethod
    def add(cls, *items: Item) -> None:
        for item in items:
            cls.items[item.id] = item

            if isinstance(item, MultiplierItem):
                cls.multipliers[item.id] = item

            elif isinstance(item, BuffItem):
                cls.buffs[item.id] = item

            elif isinstance(item, ToolItem):
                cls.tools[item.id] = item

            else:
                cls.useless[item.id] = item

    @classmethod
    def remove(cls, item_id: str) -> None:
        try:
            item = cls.items.pop(item_id)
        except KeyError:
            raise UnknownItemError(repr(item_id))

        if isinstance(item, MultiplierItem):
            cls.multipliers.pop(item.id)

        elif isinstance(item, BuffItem):
            cls.buffs.pop(item.id)

        elif isinstance(item, ToolItem):
            cls.tools.pop(item.id)

        else:
            cls.useless.pop(item.id)

    @classmethod
    def load(cls) -> None:
        item_data: dict[str, dict[str, dict[str, Any]]] = toml.load("config/items.toml")

        # Store the new items in a temporary list to avoid having an extended period of time where
        # the self.items list is empty. This should make the transition nearly instant
        new_items: list[Item] = []

        for item_id, item in item_data["multipliers"].items():
            new_items.append(MultiplierItem(item_id, **item))

        for item_id, item in item_data["buffs"].items():
            new_items.append(
                BuffItem(
                    item_id,
                    name=item["name"],
                    description=item["description"],
                    price=item["price"],
                    duration=timedelta(hours=item["duration"]),
                    cooldown=item.get("cooldown"),
                    multiplier=item.get("multiplier"),
                    specified_perks=item.get("specified_perks"),
                )
            )

        for item_id, item in item_data["tools"].items():
            new_items.append(ToolItem(item_id, **item))

        for item_id, item in item_data["useless"].items():
            new_items.append(UselessItem(item_id, **item))

        cls.items.clear()
        cls.add(*new_items)


ItemManager.load()
