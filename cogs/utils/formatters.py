import enum
import math
from collections.abc import Iterable
from datetime import timedelta
from typing import Any, Literal, overload

from . import MEME_URL


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


class Article(enum.Enum):
    DEFINITE = enum.auto()
    INDEFINITE_A = enum.auto()
    INDEFINITE_AN = enum.auto()
    INDEFINITE = enum.auto()
    NUMERAL = enum.auto()


def format_int(
    __int: int, /, format_type: IntFormatType = IntFormatType.FULL_UNIT
) -> str:
    """
    IntFormatType.FULL_UNIT -> 123.45 million

    IntFormatType.ABBREVIATED_UNIT -> 123.45M

    IntFormatType.FULL -> 123,456,789
    """
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


def format_inches(
    __inches: int,
    /,
    *,
    markdown: MarkdownFormat | None = MarkdownFormat.BOLD,
    in_between: str | None = None,
) -> str:
    if in_between is None:
        in_between = ""
    else:
        in_between += " "

    if markdown is None:
        return f"{format_int(__inches)} {in_between}inch{'' if __inches == 1 else 'es'}"

    if markdown == MarkdownFormat.BOLD:
        return f"**{format_int(__inches)}** {in_between}inch{'' if __inches == 1 else 'es'}"

    return f"**[{format_int(__inches)}]({MEME_URL}) {in_between}inch{'' if __inches == 1 else 'es'}**"


@overload
def format_time(
    duration: timedelta,
    /,
    smallest_unit: TimeUnitLiteral | None = "second",
    *,
    adjective: bool = False,
    max_decimals: int = 0,
) -> str: ...


@overload
def format_time(
    seconds: float,
    /,
    smallest_unit: TimeUnitLiteral | None = "second",
    *,
    adjective: bool = False,
    max_decimals: int = 0,
) -> str: ...


def format_time(
    __time: timedelta | float,
    /,
    smallest_unit: TimeUnitLiteral | None = "second",
    *,
    adjective: bool = False,
    max_decimals: int = 0,
) -> str:
    durations: list[str] = []

    if isinstance(__time, timedelta):
        seconds = __time.total_seconds()
    else:
        seconds = __time

    biggest_unit: TimeUnitLiteral | None = None

    for time_unit, time_unit_value in _TIME_UNITS.items():
        if biggest_unit is None:
            if seconds // time_unit_value:
                biggest_unit = time_unit
            elif (
                time_unit == smallest_unit
                and (seconds * 10**max_decimals) // time_unit_value
            ):
                biggest_unit = time_unit

        if (
            time_unit == smallest_unit
            and biggest_unit == smallest_unit
            and (seconds * 10**max_decimals) // time_unit_value
        ):
            suffix = "s"
            durations.append(
                f"{seconds / time_unit_value:,.{max_decimals}f} {time_unit}{suffix}"
            )

        elif seconds // time_unit_value:
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
        format_iterable([1, 2, 3]) -> "\\- 1\n\\- 2\n\\- 3"
        format_iterable([1, 2, 3], inline=True) -> "1, 2 and 3"
    """

    values = [str(i) for i in __iterable] or ["nothing"]

    if not inline:
        return joiner + f"\n{joiner}".join(values)

    if len(values) < 3:
        return " and ".join(values)

    last_value = values.pop()
    return f"{', '.join(values)} and {last_value}"


def format_ordinal(__ordinal: int, /) -> str:
    """
    Example:
        format_ordinal(1) -> "1st"
        format_ordinal(2) -> "2nd"
        format_ordinal(48) -> "48th"
    """

    if 10 <= __ordinal % 100 <= 20:
        suffix = "th"
    else:
        suffixes = {1: "st", 2: "nd", 3: "rd"}
        suffix = suffixes.get(__ordinal % 10, "th")

    return f"{__ordinal:,}{suffix}"


@overload
def format_amount(
    singular: str,
    plural: str,
    amount: int,
    *,
    markdown: MarkdownFormat = MarkdownFormat.BOLD,
    full_markdown: bool = False,
    article: Article | None = None,
) -> str: ...


@overload
def format_amount(
    singular: str,
    plural: str,
    amount: int,
    *,
    markdown: None,
    article: Article | None = None,
) -> str: ...


@overload
def format_amount(
    singular: str,
    plural: str,
    amount: int,
    *,
    markdown: MarkdownFormat | None = MarkdownFormat.BOLD,
    full_markdown: bool = False,
    article: Article | None = None,
) -> str: ...


def format_amount(
    singular: str,
    plural: str,
    amount: int,
    *,
    markdown: MarkdownFormat | None = MarkdownFormat.BOLD,
    full_markdown: bool = False,
    article: Article | None = None,
) -> str:
    """
    Example:
        format_amounts('knife', 'knives', 1, full_markdown=True}) -> "a **knife**"

        format_amounts('knife', 'knives', 2}) -> "**2** knives"
    """

    if amount == 1:
        prefix = ""
        prefix_markdown = False

        if article == Article.DEFINITE:
            prefix = "the "

        elif article == Article.INDEFINITE_A:
            prefix = "a "

        elif article == Article.INDEFINITE_AN:
            prefix = "an "

        elif article == Article.INDEFINITE:
            prefix = "an " if singular[0] in "aeiou" else "a "

        elif article == Article.NUMERAL:
            prefix = f"1 "
            prefix_markdown = True

        if not full_markdown or markdown is None:
            return f"{prefix}{singular}"

        if prefix_markdown:
            if markdown == MarkdownFormat.BOLD:
                return f"**{prefix}{singular}**"

            return f"**[{prefix}{singular}]({MEME_URL})**"

        if markdown == MarkdownFormat.BOLD:
            return f"{prefix}**{singular}**"

        return f"{prefix}**[{singular}]({MEME_URL})**"

    if markdown is None:
        return f"{format_int(amount)} {plural}"

    if not full_markdown:
        if markdown == MarkdownFormat.BOLD:
            return f"**{format_int(amount)}** {plural}"

        return f"**[{format_int(amount)}]({MEME_URL})** {plural}"

    if markdown == MarkdownFormat.BOLD:
        return f"**{format_int(amount)} {plural}**"

    return f"**[{format_int(amount)} {plural}]({MEME_URL})**"


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
