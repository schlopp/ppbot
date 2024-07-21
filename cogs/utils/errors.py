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
    pass
