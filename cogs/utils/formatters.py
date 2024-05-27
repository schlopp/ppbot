import enum
import math
from collections.abc import Iterable
from datetime import timedelta
from typing import Any, Literal, overload


TimeUnitLiteral = Literal[
    "year", "week", "day", "hour", "minute", "second", "millisecond"
]

_UNITS = {
    "million": "m",
    "billion": "b",
    "trillion": "t",
    "quadrillion": "q",
    "quintillion": " qt",
    "sextillion": " sext.",
    "septillion": " sept.",
    "octillion": " oct.",
    "nonillion": " non.",
    "decillion": " dec.",
    "undecillion": " und.",
    "duodecillion": " duo.",
    "tredicillion": " tre.",
    "quattuordecillion": " qua.",
    "quindecillion": " qui.",
    "sexdecillion": " sexd.",
    "septendecillion": "s epte.",
    "octodecillion": " octo.",
    "novemdecillion": " nov.",
    "vigintillion": " vig.",
}
_TIME_UNITS: dict[TimeUnitLiteral, float] = {
    "year": 60 * 60 * 24 * 365,
    "week": 60 * 60 * 24 * 7,
    "day": 60 * 60 * 24,
    "hour": 60 * 60,
    "minute": 60,
    "second": 1,
    "millisecond": 1 / 1000,
}


class IntFormatType(enum.Enum):
    FULL = enum.auto()
    FULL_UNIT = enum.auto()
    ABBREVIATED_UNIT = enum.auto()


class MarkdownFormat(enum.Enum):
    BOLD_BLUE = enum.auto()
    BOLD = enum.auto()


def format_int(
    __int: int, /, format_type: IntFormatType = IntFormatType.FULL_UNIT
) -> str:
    if format_type == IntFormatType.FULL or -(10**6) < __int < 10**6:
        return f"{__int:,}"
    else:
        unit = math.floor(math.log10(__int + 1 if not __int else abs(__int))) // 3
        unit_value = math.floor(__int / 10 ** (unit * 3) * 100) / 100

        if unit_value.is_integer():
            unit_value = math.floor(unit_value)

        try:
            unit = list(_UNITS)[unit - 2]
        except IndexError:
            if format_type == IntFormatType.FULL_UNIT:
                return "infinity"
            return "inf."

        if format_type == IntFormatType.FULL_UNIT:
            return f"{unit_value} {unit}"

        return f"{unit_value}{_UNITS[unit].upper()}"


@overload
def format_time(
    duration: timedelta,
    /,
    smallest_unit: TimeUnitLiteral | None = "second",
    *,
    adjective: bool = False,
) -> str: ...


@overload
def format_time(
    seconds: float,
    /,
    smallest_unit: TimeUnitLiteral | None = "second",
    *,
    adjective: bool = False,
) -> str: ...


def format_time(
    __time: timedelta | float,
    /,
    smallest_unit: TimeUnitLiteral | None = "second",
    *,
    adjective: bool = False,
) -> str:
    durations: list[str] = []

    if isinstance(__time, timedelta):
        seconds = __time.total_seconds()
    else:
        seconds = __time

    for time_unit, time_unit_value in _TIME_UNITS.items():
        if seconds // time_unit_value:
            suffix = "s" if seconds // time_unit_value != 1 and not adjective else ""
            durations.append(f"{int(seconds // time_unit_value)} {time_unit}{suffix}")

        if time_unit == smallest_unit:
            break

        seconds -= seconds // time_unit_value * time_unit_value

    try:
        last_duration = durations.pop()
    except IndexError:
        return f"0 {smallest_unit}s"

    if durations:
        return f"{', '.join(durations)} and {last_duration}"

    return last_duration


def format_iterable(
    __iterable: Iterable[Any], /, *, inline: bool = False, joiner: str = "- "
) -> str:
    """
    Example:
        format_iterable([1, 2, 3]) -> "1, 2 and 3"
        format_iterable([1, 2, 3], inline=False) -> "- 1\n- 2\n- 3"
    """

    values = [str(i) for i in __iterable] or ["nothing"]

    if not inline:
        return joiner + f"\n{joiner}".join(values)

    if len(values) < 3:
        return " and ".join(values)

    last_value = values.pop()
    return f"{', '.join(values)} and {last_value}"


def clean(text: str) -> str:
    markdown_replacements: dict[str, str] = {
        "*": "",
        "~": "",
        "_": "",
        "`": "",
        "\\": "",
        "[": "(",
        "]": ")",
        "https://": "",
        "http://": "",
        "<#": "#",
        "<@": "@",
        "<t:": "t:",
        "<a:": "a:",
        "<:": ":",
    }

    for character in markdown_replacements:
        text = text.replace(character, "")

    return text.strip()
