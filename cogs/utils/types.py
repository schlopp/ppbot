class Object:
    __slots__: tuple[str, ...] = ()

    def __repr__(self) -> str:
        attribute_text = " ".join(
            f"{slot}={getattr(self, slot)}"
            for slot in self.__slots__
            if not slot.startswith("_")
        )
        return f"<{self.__class__.__name__} {attribute_text}>"
