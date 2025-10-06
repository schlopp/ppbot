from __future__ import annotations
import asyncpg
import logging
import re
from datetime import timedelta
from functools import cached_property
from typing import Any, Literal, Self
from string import ascii_letters, digits

import toml
import rust_utils  # pyright: ignore[reportMissingModuleSource]
from discord.ext import commands

from . import (
    Object,
    DatabaseWrapperObject,
    DifferenceTracker,
    MarkdownFormat,
    format_slash_command,
    format_amount,
    Article,
)


class UnknownItemError(Exception):
    pass


class UselessItem(Object):
    __slots__ = ("id", "name", "plural", "description", "price", "purchasable")
    _repr_attributes = __slots__
    category = "USELESS"
    category_name = "Useless Items"

    def __init__(
        self,
        id: str,
        *,
        name: str,
        plural: str | None = None,
        indefinite_article: (
            Literal[Article.INDEFINITE_A, Article.INDEFINITE_AN, Article.INDEFINITE]
            | None
        ) = Article.INDEFINITE,
        description: str,
        price: int,
        purchasable: bool,
    ) -> None:
        self.id = id
        self.name = name
        self.plural = plural or name
        self.indefinite_article = indefinite_article
        self.description = description
        self.price = price

    def format_amount(
        self,
        amount: int,
        *,
        markdown: MarkdownFormat | None = MarkdownFormat.BOLD,
        full_markdown: bool = False,
        article: Article | None = None,
    ) -> str:
        return format_amount(
            self.name,
            self.plural,
            amount=amount,
            markdown=markdown,
            full_markdown=full_markdown,
            article=article,
        )


class LegacyItem(UselessItem):
    """
    For legacy items (usually from giveaways) / items that have not officially been added
    """

    __slots__ = (
        "id",
        "name",
        "plural",
        "indefinite_article",
        "description",
        "price",
        "purchasable",
        "season",
    )
    _repr_attributes = __slots__
    category = "LEGACY"
    category_name = "Legacy Items"

    def __init__(
        self,
        id: str,
        *,
        name: str,
        plural: str | None = None,
        indefinite_article: (
            Literal[Article.INDEFINITE_A, Article.INDEFINITE_AN, Article.INDEFINITE]
            | None
        ) = Article.INDEFINITE,
        description: str = "This is a legacy/exclusive item.",
        price: int = 0,
        purchasable: bool = False,
        season: str = "???",
    ) -> None:
        self.id = id
        self.name = name
        self.plural = plural or name
        self.indefinite_article = indefinite_article
        self.description = description
        self.price = price
        self.season = season

    @classmethod
    def from_name(cls: type[Self], name: str) -> Self:
        valid_id_chars = ascii_letters + digits + "_"
        item_id = "".join(
            char.upper()
            for char in "_".join(name.replace("_", " ").split())
            if char in valid_id_chars
        )
        return cls(item_id, name=name)


class MultiplierItem(UselessItem):
    __slots__ = ("id", "name", "plural", "description", "price", "purchasable", "gain")
    _repr_attributes = __slots__
    category = "MUTLIPLIER"
    category_name = "Multipliers"

    def __init__(
        self,
        id: str,
        *,
        name: str,
        plural: str | None = None,
        indefinite_article: (
            Literal[Article.INDEFINITE_A, Article.INDEFINITE_AN, Article.INDEFINITE]
            | None
        ) = Article.INDEFINITE,
        description: str,
        price: int,
        purchasable: bool,
        gain: int,
    ) -> None:
        self.id = id
        self.name = name
        self.plural = plural or name
        self.indefinite_article = indefinite_article
        self.description = description
        self.price = price
        self.purchasable = purchasable
        self.gain = gain

    def compute_cost(
        self, amount: int, *, current_multiplier: int = 1
    ) -> tuple[int, int]:
        """Returns `(cost: int, gain: int)`"""
        return rust_utils.compute_multiplier_item_cost(
            amount, current_multiplier, self.price, self.gain
        )

    def compute_max_purchase(
        self, *, available_inches: int, current_multiplier: int = 1
    ) -> tuple[int, int, int]:
        """Returns `(amount: int, cost: int, gain: int)`"""
        return rust_utils.compute_max_multiplier_item_purchase_amount(
            available_inches, current_multiplier, self.price, self.gain
        )


class BuffItem(UselessItem):
    __slots__ = (
        "name",
        "plural",
        "description",
        "price",
        "purchasable",
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
        indefinite_article: (
            Literal[Article.INDEFINITE_A, Article.INDEFINITE_AN, Article.INDEFINITE]
            | None
        ) = Article.INDEFINITE,
        description: str,
        price: int,
        purchasable: bool,
        duration: timedelta,
        cooldown: timedelta | None,
        multiplier: float | None,
        specified_details: list[str] | None,
    ) -> None:
        self.id = id
        self.name = name
        self.plural = plural or name
        self.indefinite_article = indefinite_article
        self.description = description
        self.price = price
        self.purchasable = purchasable
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
        "purchasable",
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
        indefinite_article: (
            Literal[Article.INDEFINITE_A, Article.INDEFINITE_AN, Article.INDEFINITE]
            | None
        ) = Article.INDEFINITE,
        description: str,
        price: int,
        purchasable: bool,
        associated_command_name: str,
    ) -> None:
        self.id = id
        self.name = name
        self.plural = plural or name
        self.indefinite_article = indefinite_article
        self.description = description
        self.price = price
        self.purchasable = purchasable
        self.associated_command_name = associated_command_name

    @property
    def associated_command_link(self) -> str:
        return format_slash_command(self.associated_command_name)


Item = UselessItem | LegacyItem | MultiplierItem | BuffItem | ToolItem


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
        return ItemManager.get(self.id, possible_legacy=True)

    def format_item(
        self,
        *,
        markdown: MarkdownFormat | None = MarkdownFormat.BOLD,
        full_markdown: bool = False,
        article: Article | None = None,
    ) -> str:
        return self.item.format_amount(
            self.amount.value,
            markdown=markdown,
            full_markdown=full_markdown,
            article=article,
        )

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
        connection: asyncpg.Connection, user_id: int, *item_ids: str, any: bool = True
    ) -> bool:
        if not item_ids:
            raise ValueError("No item ID(s) given")

        if any:
            return bool(
                await connection.fetchval(
                    f"""
                    SELECT 1
                    FROM inventories
                    WHERE
                        user_id = $1
                        AND item_id IN ({", ".join(f"${n + 2}" for n in range(len(item_ids)))})
                        AND item_amount > 0
                    """,
                    user_id,
                    *item_ids,
                )
            )
        for item_id in item_ids:
            if await connection.fetchval(
                f"""
                SELECT 1
                FROM inventories
                WHERE
                    user_id = $1
                    AND item_id = $2
                    AND item_amount > 0
                """,
                user_id,
                item_id,
            ):
                return True

        return False


class ItemManager:
    items: dict[str, Item] = {}
    multipliers: dict[str, MultiplierItem] = {}
    buffs: dict[str, BuffItem] = {}
    tools: dict[str, ToolItem] = {}
    useless: dict[str, UselessItem] = {}
    legacy: dict[str, LegacyItem] = {}
    items_by_name: dict[str, Item] = {}
    _MATCH_SLASH_COMMANDS_PATTERN = re.compile(r"<\/[A-z](?:[A-z]|[0-9]|-|\s)*>")
    _logger = logging.getLogger("vbu.bot.cog.utils.ItemManager")

    @staticmethod
    def _format_indefinite_article(item_data: dict[str, Any]) -> None:
        try:
            indefinite_article_value: str = item_data.pop("indefinite_article")
        except KeyError:
            return

        if indefinite_article_value == "none":
            item_data["indefinite_article"] = None
            return

        indefinite_article = Article[indefinite_article_value]

        if indefinite_article not in (Article.INDEFINITE_A, Article.INDEFINITE_AN):
            raise ValueError(
                f"Expected indefinite_article of item to be {Article.INDEFINITE_A!r}, "
                f" {Article.INDEFINITE_AN!r} or None, received {indefinite_article!r}"
                " instead."
            )

        item_data["indefinite_article"] = indefinite_article

    @classmethod
    def get(
        cls,
        item_key: str,
        *,
        possible_legacy: bool = False,
        attempt_capitalised_id: bool = False,
    ) -> Item:
        """
        note: when possible_legacy=True and a possibly unregistered legacy item
        is given, item_key should be the item's name, not ID
        note: attempt_capitalised_id should really only be used for data transfers,
        dont use it in code where you could just.. type the ID in capital letters?
        """

        item_id = item_key
        if attempt_capitalised_id:
            item_id = "_".join(item_id.capitalize().split())

        item = cls.items.get(item_id, cls.items_by_name.get(item_key))

        if item is None:
            if possible_legacy:
                item = LegacyItem.from_name(item_key)

                cls.items[item.id] = item
                cls.items_by_name[item.name] = item
                cls.legacy[item.id] = item

                return item

            raise UnknownItemError(repr(item_key))

        return item

    @classmethod
    def get_command_tool(cls, command_name: str) -> ToolItem:
        tools = [
            tool
            for tool in ItemManager.tools.values()
            if command_name == tool.associated_command_name
        ]

        if len(tools) > 1:
            raise ValueError(f"Multiple associated with command {command_name!r}")

        elif not tools:
            raise ValueError(f"No tool associated with command {command_name!r}")

        return tools[0]

    @classmethod
    def add(cls, *items: Item) -> None:
        for item in items:
            cls.items[item.id] = item
            cls.items_by_name[item.name] = item

            if isinstance(item, LegacyItem):
                cls.legacy[item.id] = item

            elif isinstance(item, MultiplierItem):
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

        if isinstance(item, LegacyItem):
            cls.multipliers.pop(item.id)

        elif isinstance(item, MultiplierItem):
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
            cls._format_indefinite_article(item)
            new_item = MultiplierItem(item_id, **item)
            new_items.append(new_item)
            cls._logger.info(f" * Loaded multiplier item {new_item.id!r}")

        for item_id, item in item_data["buffs"].items():
            cls._format_indefinite_article(item)
            specified_details: list[str] | None = item.get("specified_details")
            if specified_details is not None:
                for index, detail in enumerate(specified_details):
                    for slash_command in re.findall(
                        cls._MATCH_SLASH_COMMANDS_PATTERN, detail
                    ):
                        detail = detail.replace(
                            slash_command, format_slash_command(slash_command[2:-1])
                        )
                    specified_details[index] = detail

            new_item = BuffItem(
                item_id,
                name=item["name"],
                plural=item.get("plural"),
                indefinite_article=item.get("indefinite_article", Article.INDEFINITE),
                description=item["description"],
                price=item["price"],
                purchasable=item["purchasable"],
                duration=timedelta(hours=item["duration"]),
                cooldown=(
                    timedelta(hours=item["cooldown"])
                    if item.get("cooldown") is not None
                    else None
                ),
                multiplier=item.get("multiplier"),
                specified_details=specified_details,
            )

            new_items.append(new_item)
            cls._logger.info(f" * Loaded buff item {new_item.id!r}")

        for item_id, item in item_data["tools"].items():
            cls._format_indefinite_article(item)
            new_item = ToolItem(item_id, **item)
            new_items.append(new_item)
            cls._logger.info(f" * Loaded tool item {new_item.id!r}")

        for item_id, item in item_data["useless"].items():
            cls._format_indefinite_article(item)
            new_item = UselessItem(item_id, **item)
            new_items.append(new_item)
            cls._logger.info(f" * Loaded useless item {new_item.id!r}")

        for item_id, item in item_data["legacy"].items():
            cls._format_indefinite_article(item)
            new_item = LegacyItem(item_id, **item)
            new_items.append(new_item)
            cls._logger.info(f" * Loaded legacy item {new_item.id!r}")

        cls.items.clear()
        cls.add(*new_items)


class MissingTool(commands.CheckFailure):
    def __init__(self, message: str | None = None, *args: Any, tool: ToolItem) -> None:
        super().__init__(message, tool, *args)
        self.tool = tool
