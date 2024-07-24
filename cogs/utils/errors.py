from typing import Any

import discord
from discord.ext import commands


class PpMissing(commands.CheckFailure):
    def __init__(
        self,
        message: str | None = None,
        *args: Any,
        user: discord.User | discord.Member | None = None,
    ) -> None:
        super().__init__(message, *args)
        self.user = user


class PpNotBigEnough(commands.CheckFailure):
    pass


class InvalidArgumentAmount(commands.BadArgument):
    def __init__(
        self,
        message: str | None = None,
        *args: Any,
        argument: str,
        min: int | None = None,
        max: int | None = None,
        special_amounts: list[str] | None = None,
    ) -> None:
        super().__init__(message, *args)
        self.argument = argument
        self.min = min
        self.max = max

        if special_amounts is not None:
            self.special_amounts = special_amounts
        else:
            special_amounts = []
