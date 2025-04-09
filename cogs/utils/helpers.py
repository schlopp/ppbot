from __future__ import annotations
import enum
import random
from collections.abc import Mapping, Iterable
from datetime import datetime, UTC
from typing import Generic, TypeVar, Any, Literal, overload, cast, Self

import asyncpg
import discord

from . import RED, BLUE


_T_co = TypeVar("_T_co", covariant=True)


Record = Mapping[str, Any]


class RecordNotFoundError(Exception):
    pass


def limit_text(text: str, limit: int):
    assert limit >= 0
    if limit == 1:
        return text[0]
    if len(text) - 1 > limit:
        return text[0 : limit - 1] + "\N{HORIZONTAL ELLIPSIS}"
    return text


def compare(x: int, y: int) -> Literal[-1, 0, 1]:
    if x < y:
        return -1
    if x == y:
        return 0
    return 1


def find_nearest_number(
    numbers: Iterable[int], number: int
) -> tuple[int, Literal[-1, 0, 1]]:
    """Returns `(nearest_number: int, comparison: L[-1, 0, 1])`"""
    nearest_number: int | None = None
    for i in numbers:
        if i == number:
            return i, 0
        if i < number:
            nearest_number = i
            continue
        if nearest_number is None:
            return i, 1
        match compare(abs(nearest_number - number), abs(i - number)):
            case -1:
                return nearest_number, -1
            case 0:
                if random.randint(0, 1):
                    return nearest_number, -1
                return i, 1
            case 1:
                return i, 1
        nearest_number = i
    if nearest_number is None:
        raise ValueError("Empty numbers iterable given")
    return nearest_number, -1


class Embed(discord.Embed):
    TIPS = ["There is no tip, take off your clothes."]

    def __init__(self, *args, color=BLUE, **kwargs) -> None:
        super().__init__(*args, color=color, **kwargs)

    def add_tip(self) -> None:
        if not random.randint(0, 5):
            self.add_field(name="TIP:", value=random.choice(self.TIPS), inline=False)

    @classmethod
    def as_timeout(cls, action: str):
        return cls(
            colour=RED,
            title=f"{action} - you took too long",
            description="Next time, click the buttons faster and don't go AFK",
        )


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


class RowLevelLockMode(enum.Enum):
    FOR_UPDATE = "UPDATE"
    FOR_NO_KEY_UPDATE = "NO KEY UPDATE"
    FOR_KEY_SHARE = "KEY SHARE"


class DatabaseWrapperObject(Object):
    _table: str
    _columns: dict[str, str] = {}
    _column_attributes: dict[str, str] = {}
    _identifier_attributes: tuple[str, ...] = ()
    _trackers: tuple[str, ...] = ()

    def _generate_pgsql_set_query(
        self, *, argument_position: int = 1
    ) -> None | tuple[str, list[int | str], int]:
        update_values: list[str] = []
        query_arguments: list[int | str] = []

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
    ) -> tuple[str, list, int]:
        """Returns `(query: str, query_args: int, arg_position: int)`"""
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

    @classmethod
    def _generate_pgsql_insert_query(
        cls, required_values: dict[str, Any], *, argument_position: int = 1
    ) -> tuple[str, list, int]:
        """Returns `(query: str, query_args: int, arg_position: int)`"""
        query_insert_parts: list[str] = []
        query_value_parts: list[str] = []
        query_arguments = []

        for required_attribute, required_value in required_values.items():
            query_arguments.append(required_value)
            query_insert_parts.append(cls._column_attributes[required_attribute])
            query_value_parts.append(f"${argument_position}")
            argument_position += 1

        return (
            f"INSERT INTO {cls._table}"
            f" ({', '.join(query_insert_parts)})"
            f" VALUES ({', '.join(query_value_parts)})",
            query_arguments,
            argument_position,
        )

    def _generate_pgsql_where_query(
        self, *, argument_position: int = 1
    ) -> tuple[str, list, int]:
        """Returns `(query: str, query_args: int, arg_position: int)`"""
        sql_conditions: list[str] = []
        query_arguments = []

        for identifier_attribute in self._identifier_attributes:
            query_arguments.append(getattr(self, identifier_attribute))
            sql_conditions.append(
                f"{self._column_attributes[identifier_attribute]}=${argument_position}"
            )
            argument_position += 1

        return (
            f"WHERE {' AND '.join(sql_conditions)}" if sql_conditions else "",
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
        return cls(**{cls._columns[column]: value for column, value in record.items()})  # type: ignore

    @overload
    @classmethod
    async def fetch_record(
        cls,
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        selected_columns: Iterable[str] | None = None,
        *,
        lock: Literal[None] = None,
        fetch_multiple_rows: Literal[True],
        timeout: float | None = None,
        insert_if_not_found: bool = False,
    ) -> list[Record]: ...

    @overload
    @classmethod
    async def fetch_record(
        cls,
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        selected_columns: Iterable[str] | None = None,
        *,
        lock: RowLevelLockMode | None = None,
        fetch_multiple_rows: Literal[False] = False,
        timeout: float | None = None,
        insert_if_not_found: bool = False,
    ) -> Record: ...

    @classmethod
    async def fetch_record(
        cls,
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        selected_columns: Iterable[str] | None = None,
        *,
        lock: RowLevelLockMode | None = None,
        fetch_multiple_rows: bool = False,
        timeout: float | None = None,
        insert_if_not_found: bool = False,
    ) -> Record | list[Record]:
        where_query, where_query_arguments, _ = cls._generate_cls_pgsql_where_query(
            required_values
        )
        query = f"{cls._generate_cls_pgsql_select_query(selected_columns)} FROM {cls._table} {where_query}"

        if lock is not None:
            query += f" FOR {lock.value}"

        if fetch_multiple_rows:
            return await connection.fetch(
                query, *where_query_arguments, timeout=timeout
            )
        record = cast(
            Record | None,
            await connection.fetchrow(query, *where_query_arguments, timeout=timeout),
        )
        if record is not None:
            return record

        if insert_if_not_found:
            insert_query, insert_query_args, _ = cls._generate_pgsql_insert_query(
                required_values
            )
            await connection.execute(
                insert_query, *insert_query_args, timeout=timeout  # type: ignore
            )
            return await cls.fetch_record(
                connection,
                required_values,
                selected_columns,
                lock=lock,
                fetch_multiple_rows=fetch_multiple_rows,
                timeout=timeout,
                insert_if_not_found=True,
            )

        raise RecordNotFoundError(
            f"Couldn't find a record derived from the SQL statement {query!r} with the arguments"
            f" {where_query_arguments}. Use kwarg insert_if_not_found=True if you mean't to insert"
            " instead of raising an error."
        )

    @overload
    @classmethod
    async def fetch(
        cls: type[Self],
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        *,
        lock: Literal[None] = None,
        fetch_multiple_rows: Literal[True],
        timeout: float | None = None,
        insert_if_not_found: bool = False,
    ) -> list[Self]: ...

    @overload
    @classmethod
    async def fetch(
        cls: type[Self],
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        *,
        lock: RowLevelLockMode | None = None,
        fetch_multiple_rows: Literal[False] = False,
        timeout: float | None = None,
        insert_if_not_found: bool = False,
    ) -> Self: ...

    @classmethod
    async def fetch(
        cls: type[Self],
        connection: asyncpg.Connection,
        required_values: dict[str, Any],
        *,
        lock: RowLevelLockMode | None = None,
        fetch_multiple_rows: bool = False,
        timeout: float | None = None,
        insert_if_not_found: bool = False,
    ) -> Self | list[Self]:
        if fetch_multiple_rows:
            return [
                cls.from_record(record)
                for record in await cls.fetch_record(
                    connection,
                    required_values,
                    fetch_multiple_rows=True,
                    timeout=timeout,
                    insert_if_not_found=insert_if_not_found,
                )
            ]
        record = await cls.fetch_record(
            connection,
            required_values,
            lock=lock,
            timeout=timeout,
            insert_if_not_found=insert_if_not_found,
        )

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


class DifferenceTracker(Object, Generic[_T_co]):
    __slots__ = ("value", "__start_value", "column")
    _repr_attributes = ("value", "start_value", "difference", "column")

    def __init__(self, start_value: _T_co, *, column: str | None = None) -> None:
        self.value: _T_co = start_value
        self.__start_value: _T_co = start_value
        self.column = column

    @property
    def start_value(self) -> _T_co:
        return self.__start_value

    @property
    def difference(self) -> _T_co | None:
        if self.value == self.start_value:
            return None
        if isinstance(self.value, int):
            assert isinstance(self.start_value, int)
            return self.value - self.start_value
        return self.value


class IntegerHolder(int, Object):
    """
    Stores an integer inside a class so that it can be used multiple times as a value for an enum
    """

    _repr_attributes = ("value",)

    def __init__(self, value: int):
        self.value = value

    def __int__(self):
        return self.value

    def __add__(self, other: int):
        return self.value + other

    def __sub__(self, other: int):
        return self.value - other

    def __mul__(self, other: int):
        return self.value * other

    def __truediv__(self, other: int):
        return self.value / other

    def __floordiv__(self, other: int):
        return self.value // other

    def __mod__(self, other: int):
        return self.value % other

    def __pow__(self, other: int):  # type: ignore
        return self.value**other


def is_weekend() -> bool:
    """Returns true on friday, saturday and sunday (UTC)"""
    return datetime.now(UTC).weekday() >= 4
