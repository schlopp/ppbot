from __future__ import annotations
import asyncpg
from datetime import timedelta
from decimal import Decimal
from functools import cached_property
from typing import Any

import toml

from . import (
    Object,
    DatabaseWrapperObject,
    DifferenceTracker,
    MarkdownFormat,
    format_int,
    MEME_URL,
)


class UnknownItemError(Exception):
    pass


class UselessItem(Object):
    __slots__ = ("id", "name", "plural", "description", "price")
    _repr_attributes = __slots__
    category = "USELESS"
    category_name = "Useless Items"

    def __init__(
        self,
        id: str,
        *,
        name: str,
        plural: str | None = None,
        description: str,
        price: int,
    ) -> None:
        self.id = id
        self.name = name
        self.plural = plural or name
        self.description = description
        self.price = price

    def format_amount(
        self, amount: int, *, markdown: MarkdownFormat | None = MarkdownFormat.BOLD
    ) -> str:
        name = self.name if amount == 1 else self.plural

        if markdown is None:
            return f"{format_int(amount)} {name}"

        if markdown == MarkdownFormat.BOLD:
            return f"**{format_int(amount)}** {name}"

        return f"**[{format_int(amount)}]({MEME_URL})** {name}"


class MultiplierItem(UselessItem):
    __slots__ = ("id", "name", "plural", "description", "price", "gain")
    _repr_attributes = __slots__
    category = "MUTLIPLIER"
    category_name = "Multipliers"

    def __init__(
        self,
        id: str,
        *,
        name: str,
        plural: str | None = None,
        description: str,
        price: int,
        gain: int,
    ) -> None:
        self.id = id
        self.name = name
        self.plural = plural or name
        self.description = description
        self.price = price
        self.gain = gain

    def get_scaled_values(self, amount: int, *, multiplier: int) -> tuple[int, int]:
        price = 0
        gain = 0
        exponent = Decimal("1.3")  # to avoid OverflowError's with big ass floats
        price = int(self.price * (1 - exponent ** (multiplier + amount)) / (1 - exponent))
        gain = self.gain * amount
        return price, gain


class BuffItem(UselessItem):
    __slots__ = (
        "name",
        "plural",
        "description",
        "price",
        "duration",
        "cooldown",
        "multiplier",
        "specified_details",
    )
    _repr_attributes = __slots__
    category = "BUFF"
    category_name = "Buffs"

    def __init__(
        self,
        id: str,
        *,
        name: str,
        plural: str | None = None,
        description: str,
        price: int,
        duration: timedelta,
        cooldown: timedelta | None,
        multiplier: float | None,
        specified_details: list[str] | None,
    ) -> None:
        self.id = id
        self.name = name
        self.plural = plural or name
        self.description = description
        self.price = price
        self.multiplier = multiplier
        self.duration = duration
        self.cooldown = cooldown

        if specified_details:
            self.specified_details = specified_details
        else:
            self.specified_details = []


class ToolItem(UselessItem):
    __slots__ = (
        "id",
        "name",
        "plural",
        "description",
        "price",
        "associated_command_name",
    )
    _repr_attributes = __slots__
    category = "TOOL"
    category_name = "Tools"

    def __init__(
        self,
        id: str,
        *,
        name: str,
        plural: str | None = None,
        description: str,
        price: int,
        associated_command_name: str,
    ) -> None:
        self.id = id
        self.name = name
        self.plural = plural or name
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

    @cached_property
    def item(self) -> Item:
        return ItemManager.get(self.id)

    def format_item(
        self, *, markdown: MarkdownFormat | None = MarkdownFormat.BOLD
    ) -> str:
        return self.item.format_amount(self.amount.value)

    async def update(
        self,
        connection: asyncpg.Connection,
        *,
        ensure_difference: bool = True,
        additional: bool = False,
    ):
        if ensure_difference and self.amount.difference is None:
            return

        if not self.amount.value and not additional:
            await connection.execute(
                "DELETE FROM inventories WHERE user_id=$1 AND item_id=$2",
                self.user_id,
                self.id,
            )
            return

        await connection.execute(
            f"""
            INSERT INTO inventories
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, item_id)
            DO UPDATE SET item_amount={'inventories.item_amount+' if additional else ''}$3
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
    items_by_name: dict[str, Item] = {}

    @classmethod
    def get(cls, item_key: str) -> Item:
        try:
            return cls.items[item_key]
        except KeyError:
            try:
                return cls.items_by_name[item_key]
            except KeyError:
                raise UnknownItemError(repr(item_key))

    @classmethod
    def add(cls, *items: Item) -> None:
        for item in items:
            cls.items[item.id] = item
            cls.items_by_name[item.name] = item

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

        cls.items_by_name.pop(item.name)

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
                    plural=item.get("plural"),
                    description=item["description"],
                    price=item["price"],
                    duration=timedelta(hours=item["duration"]),
                    cooldown=timedelta(hours=item["cooldown"])
                    if item.get("cooldown") is not None
                    else None,
                    multiplier=item.get("multiplier"),
                    specified_details=item.get("specified_details"),
                )
            )

        for item_id, item in item_data["tools"].items():
            new_items.append(ToolItem(item_id, **item))

        for item_id, item in item_data["useless"].items():
            new_items.append(UselessItem(item_id, **item))

        cls.items.clear()
        cls.add(*new_items)


ItemManager.load()
