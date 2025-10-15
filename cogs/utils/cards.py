from __future__ import annotations
import random
from typing import overload, Literal, Self
from enum import StrEnum, IntEnum

from . import Object, IntegerHolder


class Suit(StrEnum):
    CLUBS = "♣"
    DIAMONDS = "♦"
    HEARTS = "♥"
    SPADES = "♠"


class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = IntegerHolder(10)
    QUEEN = IntegerHolder(10)
    KING = IntegerHolder(10)
    JACK = IntegerHolder(10)
    ACE = 11


class Card(Object):
    _repr_attributes = ("rank", "suit")

    def __init__(self, rank: Rank, suit: Suit):
        self.rank = rank
        self.suit = suit

    def __str__(self) -> str:
        return f"{self.rank.name.title()} of {self.suit.name.lower()}"

    def __format__(self, format_spec: str):
        if format_spec in ["", "l"]:
            return str(self)
        if format_spec == "m":
            return f"{self.suit.value} {self.rank.name.title()}"
        if format_spec == "s":
            return (
                f"{self.suit.value}{self.rank.value if self.rank.value != 11 else 'A'}"
            )
        raise ValueError(f"Invalid format specification {format_spec!r}")

    @classmethod
    def random(cls: type[Self]) -> Self:
        return cls(random.choice(tuple(Rank)), random.choice(tuple(Suit)))


class Deck(Object):
    _repr_attributes = ("cards",)

    def __init__(self):
        self.cards = [Card(rank, suit) for rank in Rank for suit in Suit]

    def shuffle(self):
        random.shuffle(self.cards)

    @overload
    def draw(self, amount: Literal[1] = 1, *, hand: Hand | None = None) -> Card: ...

    @overload
    def draw(self, amount: int, *, hand: Hand | None = None) -> list[Card]: ...

    def draw(self, amount: int = 1, *, hand: Hand | None = None) -> Card | list[Card]:
        cards = [self.cards.pop() for _ in range(amount)]
        if hand is not None:
            hand.add(*cards)
        if len(cards) == 1:
            return cards[0]
        return cards


class Hand(Object):
    _repr_attributes = ("cards",)

    def __init__(self):
        self.cards: list[Card] = []

    def add(self, *cards: Card):
        if not cards:
            self.cards.append(Card.random())
            return

        self.cards.extend(cards)

    def __str__(self) -> str:
        return ", ".join(map(str, self.cards))

    def __format__(self, format_spec: str):
        return " ".join(f"`{card:{format_spec}}`" for card in self.cards)


class BlackjackHand(Hand):
    _repr_attributes = ("cards", "hide_second_card")

    def __init__(self, *, hide_second_card: bool = False):
        super().__init__()
        self.hide_second_card = hide_second_card

    def calculate_total(self) -> tuple[int, bool]:
        total = 0
        soft = False
        aces = 0

        for card in self.cards:
            if card.rank == Rank.ACE:
                aces += 1
                continue

            total += card.rank.value

        while aces:
            if total + 11 * aces > 21:
                total += 1
            else:
                total += 11
                soft = True
            aces -= 1

        return total, soft

    def __format__(self, format_spec: str):
        if self.hide_second_card:
            return f"`{self.cards[0]:{format_spec}}` `??`"
        return " ".join(f"`{card:{format_spec}}`" for card in self.cards)
