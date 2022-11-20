from __future__ import annotations
from typing import Generic, TypeVar


_T_co = TypeVar("_T_co", covariant=True)


class Object:
    _repr_attributes: tuple[str, ...] = ()

    def __repr__(self) -> str:
        attribute_text = " ".join(
            f"{attribute_name}={getattr(self, attribute_name)}"
            for attribute_name in self._repr_attributes
            if not attribute_name.startswith("_")
        )
        return f"<{self.__class__.__name__}{' ' if attribute_text else ''}{attribute_text}>"

    def pretty_print(self, *, indent: int = 4, prefix: str = "", indent_level: int = 0):
        if not self._repr_attributes or not indent:
            print(repr(self))
            return

        full_prefix = (prefix + " " * (indent - len(prefix))) * indent_level
        added_full_prefix = (prefix + " " * (indent - len(prefix))) * (indent_level + 1)
        print(f"{full_prefix}<{self.__class__.__name__}")
        for attribute_name in self._repr_attributes:
            attribute = getattr(self, attribute_name)
            if isinstance(attribute, Object):
                attribute.pretty_print(
                    prefix=prefix, indent=indent, indent_level=indent_level + 1
                )
                continue
            print(f"{added_full_prefix}{attribute_name}={repr(attribute)}")
        print(f"{full_prefix}>")


class DifferenceTracker(Object, Generic[_T_co]):
    __slots__ = ("value", "__start_value", "column")
    _repr_attributes = ("value", "start_value", "difference", "column")

    def __init__(self, start_value: _T_co, *, column: str | None = None) -> None:
        self.value = start_value
        self.__start_value = start_value
        self.column = column

    @property
    def start_value(self) -> _T_co:
        return self.__start_value

    @property
    def difference(self) -> _T_co | None:
        if self.value == self.start_value:
            return None
        if isinstance(self.value, int):
            return self.value - self.start_value
        return self.value
