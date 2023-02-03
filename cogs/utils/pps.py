from . import DatabaseWrapperObject, DifferenceTracker, format_int, MEME_URL


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

    def format_growth(self, growth: int | None = None) -> str:
        if growth is None:
            growth = self.size.difference or 0
        return f"**[{format_int(growth)}]({MEME_URL}) inches**"
