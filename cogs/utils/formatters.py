import enum
import math
from collections.abc import Iterable
from typing import Any


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


def format_int(value: int, format_type: IntFormatType = IntFormatType.FULL_UNIT) -> str:
    if format_type == IntFormatType.FULL or -(10**6) < value < 10**6:
        return f"{value:,}"
    else:
        unit = math.floor(math.log10(value + 1 if not value else abs(value))) // 3
        unit_value = math.floor(value / 10 ** (unit * 3) * 100) / 100

        if unit_value.is_integer():
            unit_value = math.floor(unit_value)

        if format_type == IntFormatType.FULL_UNIT:
            return f"{unit_value} {_UNITS[unit - 2]}"

        return f"{unit_value}{_UNITS[unit - 2][0].upper()}"


def format_time(value: float, smallest_unit: str | None = "second") -> str:
    durations: list[str] = []

    for time_unit, time_unit_value in _TIME_UNITS.items():
        if value // time_unit_value:
            plural = "s" if value // time_unit_value != 1 else ""
            durations.append(f"{int(value // time_unit_value)} {time_unit}{plural}")

        if time_unit == smallest_unit:
            break

        value -= value // time_unit_value * time_unit_value

    try:
        last_duration = durations.pop()
    except IndexError:
        return f"0 {smallest_unit}s"

    if durations:
        return f"{', '.join(durations)} and {last_duration}"

    return last_duration


def format_iterable(value: Iterable[Any], *, inline: bool = False) -> str:
    values = [str(i) for i in value] or ["nothing"]

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
