from __future__ import annotations
import random
from typing import overload, Literal
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
        if format_spec == "":
            return str(self)
        if format_spec == "blackjack":
            return f"`{self.suit.value} {self.rank.name.title()}`"
        raise ValueError(f"Invalid format specification {format_spec!r}")


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
            hand.give(*cards)
        if len(cards) == 1:
            return cards[0]
        return cards


class Hand(Object):
    _repr_attributes = ("cards",)

    def __init__(self):
        self.cards: list[Card] = []

    def give(self, *cards: Card):
        self.cards.extend(cards)

    def __str__(self) -> str:
        return ", ".join(map(str, self.cards))

    def __format__(self, format_spec: str):
        if format_spec == "":
            return str(self)
        if format_spec == "blackjack":
            return " ".join(f"{card:blackjack}" for card in self.cards)
        raise ValueError(f"Invalid format specification {format_spec!r}")


class BlackjackHand(Hand):
    _repr_attributes = ("cards", "hide_second_card")

    def __init__(self, *, hide_second_card: bool = False):
        super().__init__()
        self.hide_second_card = hide_second_card

    @property
    def total(self) -> int:
        total = 0
        for card in self.cards:
            total += card.rank.value
        return total

    @property
    def visual_total(self) -> int:
        total = 0
        if self.hide_second_card and len(self.cards) == 2:
            return self.cards[0].rank.value
        return total
