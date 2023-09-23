from discord.ext import commands, vbu

from cogs.utils.bot import Bot
from . import utils


class LoadingCog(vbu.Cog[utils.Bot]):
    def __init__(self, bot: Bot, logger_name: str | None = None):
        super().__init__(bot, logger_name)
        if bot.is_ready():
            bot.loop.create_task(self.load_managers())

    @commands.Cog.listener("on_ready")
    async def load_managers(self) -> None:
        await utils.SlashCommandMappingManager.load(self.bot)
        self.logger.info("Loaded SlashCommandMappingManager")


def setup(bot: utils.Bot):
    bot.add_cog(LoadingCog(bot))
