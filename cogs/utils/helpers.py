from __future__ import annotations
import enum
import math
import random
import sys
from collections.abc import Mapping, Iterable
from typing import Generic, TypeVar, Any, Literal, overload

import asyncpg  # type: ignore
import discord

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


_IntStrT_co = TypeVar("_IntStrT_co", str, int, covariant=True)


Record = Mapping[str, Any]


RED = discord.Colour(16007990)
GREEN = discord.Colour(5025616)
BLUE = discord.Colour(2201331)
PINK = discord.Colour(15418782)
UNITS = ["million", "billion", "trillion", "quadrillion"]


def limit_text(text: str, limit: int):
    assert limit >= 0
    if limit == 1:
        return text[0]
    if len(text) - 1 > limit:
        return text[0 : limit - 1] + "\N{HORIZONTAL ELLIPSIS}"
    return text


def compare(x: int, y: int) -> int:
    if x < y:
        return -1
    if x == y:
        return 0
    return 1


def find_nearest_number(
    numbers: Iterable[int], number: int
) -> tuple[int, Literal[-1, 0, 1]]:
    nearest_number: int | None = None
    for i in numbers:
        if i > number:
            if nearest_number is not None:
                match compare(abs(nearest_number - number), abs(i - number)):
                    case -1:
                        return nearest_number, -1
                    case 0:
                        return random.choice([(nearest_number, -1), (i, 1)])
                    case _:
                        return i, 1
            return i
        if i == number:
            return i, 0
        nearest_number = i
    return nearest_number, -1


class IntFormatType(enum.Enum):
    FULL = enum.auto()
    FULL_UNIT = enum.auto()
    ABBREVIATED_UNIT = enum.auto()


def format_int(value: int, format_type: IntFormatType = IntFormatType.FULL_UNIT) -> str:
    if format_type == IntFormatType.FULL or -(10**6) < value < 10**6:
        return f"{value:,}"
    else:
        unit = math.floor(math.log10(value + 1 if not value else abs(value))) // 3
        unit_value = math.floor(value / 10 ** (unit * 3) * 100) / 100

        if unit_value.is_integer():
            unit_value = math.floor(unit_value)

        if format_type == IntFormatType.FULL_UNIT:
            return f"{unit_value} {UNITS[unit - 2]}"

        return f"{unit_value}{UNITS[unit - 2][0].upper()}"


class Object:
    _repr_attributes: tuple[str, ...] = ()

    def __repr__(self) -> str:
        attribute_text = " ".join(
            f"{attribute_name}={getattr(self, attribute_name)}"
            for attribute_name in self._repr_attributes
            if not attribute_name.startswith("_")
        )
        return f"<{self.__class__.__name__}{' ' if attribute_text else ''}{attribute_text}>"

    def pretty_print(
        self,
        *,
        indent: int = 4,
        prefix: str = "",
        indent_level: int = 0,
        attribute_name: str | None = None,
    ):
        if not self._repr_attributes or not indent:
            print(repr(self))
            return

        full_prefix = (prefix + " " * (indent - len(prefix))) * indent_level
        added_full_prefix = (prefix + " " * (indent - len(prefix))) * (indent_level + 1)
        print(
            f"{full_prefix}{'' if attribute_name is None else attribute_name + '='}<{self.__class__.__name__}"
        )
        for attribute_name in self._repr_attributes:
            attribute = getattr(self, attribute_name)
            if isinstance(attribute, Object):
                attribute.pretty_print(
                    prefix=prefix,
                    indent=indent,
                    indent_level=indent_level + 1,
                    attribute_name=attribute_name,
                )
                continue
            print(f"{added_full_prefix}{attribute_name}={repr(attribute)}")
        print(f"{full_prefix}>")


class DatabaseWrapperObject(Object):
    _table: str
    _columns: dict[str, str] = {}
    _column_attributes: dict[str, str] = {}
    _identifier_attributes: tuple[str, ...] = ()
    _trackers: tuple[str, ...] = ()

    def _generate_pgsql_set_query(
        self, *, argument_position: int = 1
    ) -> None | tuple[str, list[int | str],]:
        update_values: list[str] = []
        query_arguments = []

        for tracker_attribute_name in self._trackers:
            tracker = getattr(self, tracker_attribute_name)
            if not isinstance(tracker, DifferenceTracker):
                raise TypeError(
                    f"Expected atrribute {tracker_attribute_name!r} to be of type DifferenceTracker, "
                    f"got {type(tracker)!r}"
                )

            if tracker.difference is None:
                continue

            assert tracker.column is not None

            if isinstance(tracker.difference, int | str):
                update_values.append(f"{tracker.column}=${argument_position}")
            else:
                raise TypeError(
                    f"Expected DifferenceTracker {tracker!r}'s value to be of type int or str, "
                    f"got {type(tracker.value)!r}"
                )

            query_arguments.append(tracker.value)
            argument_position += 1
        return (
            (f"SET {', '.join(update_values)}", query_arguments, argument_position)
            if update_values
            else None
        )

    @classmethod
    def _generate_cls_pgsql_where_query(
        cls, required_values: dict[str, Any], *, argument_position: int = 1
    ) -> tuple[str, list[str], int]:
        conditional_values: list[str] = []
        query_arguments = []

        for required_column, required_value in required_values.items():
            query_arguments.append(required_value)
            conditional_values.append(
                f"{cls._column_attributes[required_column]}=${argument_position}"
            )
            argument_position += 1

        return (
            f"WHERE {' AND '.join(conditional_values)}" if conditional_values else "",
            query_arguments,
            argument_position,
        )

    def _generate_pgsql_where_query(
        self, *, argument_position: int = 1
    ) -> tuple[str, list[str], int]:
        conditional_values = []
        query_arguments = []

        for identifier_attribute in self._identifier_attributes:
            query_arguments.append(getattr(self, identifier_attribute))
            conditional_values.append(
                f"{self._column_attributes[identifier_attribute]}=${argument_position}"
            )
            argument_position += 1

        return (
            f"WHERE {' AND '.join(conditional_values)}" if conditional_values else "",
            query_arguments,
            argument_position,
        )

    @classmethod
    def _generate_cls_pgsql_select_query(
        cls, selected_columns: Iterable[str] | None = None
    ) -> str:
        columns = selected_columns if selected_columns is not None else "*"
        return f"SELECT {', '.join(columns)}"

    @classmethod
    def from_record(cls: type[Self], record: Record) -> Self:
        return cls(**{cls._columns[column]: value for column, value in record.items()})

    @overload
    @classmethod
    async def fetch_record(
        cls: type[Self],
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        selected_columns: Iterable[str] | None = None,
        *,
        fetch_multiple_rows: bool = True,
    ) -> list[Record] | None:
        ...

    @overload
    @classmethod
    async def fetch_record(
        cls: type[Self],
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        selected_columns: Iterable[str] | None = None,
        *,
        lock_for_update: bool = False,
    ) -> Record | None:
        ...

    @classmethod
    async def fetch_record(
        cls: type[Self],
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        selected_columns: Iterable[str] | None = None,
        *,
        lock_for_update: bool = False,
        fetch_multiple_rows: bool = False,
    ) -> Record | list[Record] | None:
        where_query, where_query_arguments, _ = cls._generate_cls_pgsql_where_query(
            required_values
        )
        query = f"{cls._generate_cls_pgsql_select_query(selected_columns)} FROM {cls._table} {where_query}"

        if lock_for_update:
            query += " FOR UPDATE"

        if fetch_multiple_rows:
            rows: list[Record] = await connection.fetch(query, *where_query_arguments)
            if not rows:
                return None
            return rows
        record: Record = await connection.fetchrow(query, *where_query_arguments)
        if record is None:
            return None
        return record

    @overload
    @classmethod
    async def fetch(
        cls: type[Self],
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        *,
        fetch_multiple_rows: Literal[True],
    ) -> list[Self] | None:
        ...

    @overload
    @classmethod
    async def fetch(
        cls: type[Self],
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        *,
        lock_for_update: Literal[True],
    ) -> Self | None:
        ...

    @classmethod
    async def fetch(
        cls: type[Self],
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        *,
        lock_for_update: bool = False,
        fetch_multiple_rows: bool = False,
    ) -> Self | list[Self] | None:
        if fetch_multiple_rows:
            records = await cls.fetch_record(
                connection, required_values, fetch_multiple_rows=True
            )
            if not records:
                return None
            return [cls.from_record(record) for record in records]
        record: Record = await cls.fetch_record(
            connection, required_values, lock_for_update=True
        )
        if record is None:
            return None

        return cls.from_record(record)

    async def update(self, connection: asyncpg.Connection) -> None:
        set_query_result = self._generate_pgsql_set_query()
        if set_query_result is None:
            return
        set_query, set_arguments, argument_position = set_query_result
        where_query, where_arguments, _ = self._generate_pgsql_where_query(
            argument_position=argument_position
        )
        query = f"UPDATE {self._table} {set_query} {where_query}"
        await connection.execute(query, *set_arguments, *where_arguments)


class DifferenceTracker(Object, Generic[_IntStrT_co]):
    __slots__ = ("value", "__start_value", "column")
    _repr_attributes = ("value", "start_value", "difference", "column")

    def __init__(self, start_value: _IntStrT_co, *, column: str | None = None) -> None:
        self.value = start_value
        self.__start_value = start_value
        self.column = column

    @property
    def start_value(self) -> _IntStrT_co:
        return self.__start_value

    @property
    def difference(self) -> _IntStrT_co | None:
        if self.value == self.start_value:
            return None
        if isinstance(self.value, int):
            return self.value - self.start_value
        return self.value
