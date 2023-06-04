import enum
import math
from collections.abc import Iterable
from typing import Any, Literal


_UNITS = [
    "million",
    "billion",
    "trillion",
    "quadrillion",
    "quintillion",
    "sextillion",
    "septillion",
    "octillion",
    "nonillion",
    "decillion",
    "undecillion",
    "duodecillion",
    "tredicillion",
    "quattuordecillion",
    "quindecillion",
    "sexdecillion",
    "septendecillion",
    "octodecillion",
    "novemdecillion",
    "vigintillion",
]
_TIME_UNITS: dict[str, float] = {
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

        if format_type == IntFormatType.FULL_UNIT:
            return f"{unit_value} {_UNITS[unit - 2]}"

        return f"{unit_value}{_UNITS[unit - 2][0].upper()}"


def format_time(
    __seconds: float,
    /,
    smallest_unit: Literal[
        "year", "week", "day", "hour", "minute", "second", "millisecond"
    ]
    | None = "second",
) -> str:
    durations: list[str] = []

    for time_unit, time_unit_value in _TIME_UNITS.items():
        if __seconds // time_unit_value:
            suffix = "s" if __seconds // time_unit_value != 1 else ""
            durations.append(f"{int(__seconds // time_unit_value)} {time_unit}{suffix}")

        if time_unit == smallest_unit:
            break

        __seconds -= __seconds // time_unit_value * time_unit_value

    try:
        last_duration = durations.pop()
    except IndexError:
        return f"0 {smallest_unit}s"

    if durations:
        return f"{', '.join(durations)} and {last_duration}"

    return last_duration


def format_iterable(__iterable: Iterable[Any], /, *, inline: bool = False) -> str:
    values = [str(i) for i in __iterable] or ["nothing"]

    if not inline:
        return "• " + "\n• ".join(values)

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
    }

    for character in markdown_replacements:
        text = text.replace(character, "")

    return text.strip()
