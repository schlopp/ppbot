import enum

from . import DatabaseWrapperObject, DifferenceTracker, format_int, MEME_URL


class PpGrowthMarkdown(enum.Enum):
    BOLD_BLUE = enum.auto()
    BOLD = enum.auto()


class Pp(DatabaseWrapperObject):
    __slots__ = ("user_id", "multiplier", "size", "name")
    _repr_attributes = __slots__
    _table = "pps"
    _columns = {
        "user_id": "user_id",
        "pp_multiplier": "multiplier",
        "pp_size": "size",
        "pp_name": "name",
    }
    _column_attributes = {attribute: column for column, attribute in _columns.items()}
    _identifier_attributes = ("user_id",)
    _trackers = ("multiplier", "size", "name")

    def __init__(self, user_id: int, multiplier: int, size: int, name: str) -> None:
        self.user_id = user_id
        self.multiplier = DifferenceTracker(multiplier, column="pp_multiplier")
        self.size = DifferenceTracker(size, column="pp_size")
        self.name = DifferenceTracker(name, column="pp_name")

    def grow(self, growth: int, *, include_multipliers: bool = True) -> int:
        if include_multipliers:
            growth *= self.multiplier.value
        self.size.value += growth
        return growth

    def format_growth(
        self,
        growth: int | None = None,
        *,
        markdown: PpGrowthMarkdown | None = PpGrowthMarkdown.BOLD,
        prefixed: bool = False,
    ) -> str:
        if growth is None:
            growth = self.size.difference or 0

        if prefixed:
            if growth < 0:
                prefix = "lost "
                growth = abs(growth)
            else:
                prefix = "earned "
        else:
            prefix = ""

        if not markdown:
            return prefix + f"{format_int(growth)} inches"

        if markdown == PpGrowthMarkdown.BOLD:
            return prefix + f"**{format_int(growth)}** inches"

        return prefix + f"**[{format_int(growth)}]({MEME_URL}) inches**"
