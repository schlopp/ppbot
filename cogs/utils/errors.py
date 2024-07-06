from discord.ext import commands


class PpMissing(commands.CheckFailure):
    pass


class PpNotBigEnough(commands.CheckFailure):
    pass


class MissingTool(commands.CheckFailure):
    pass


class InvalidArgumentAmount(commands.BadArgument):
    pass
