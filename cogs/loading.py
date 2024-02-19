from discord.ext import commands, vbu

from . import utils


class LoadingCog(vbu.Cog[utils.Bot]):
    def __init__(self, bot: utils.Bot, logger_name: str | None = None):
        super().__init__(bot, logger_name)
        bot_ready_on_init = bot.is_ready()

        self.load_sync_managers()

        if bot_ready_on_init:
            bot.loop.create_task(self.load_async_managers())

    def load_sync_managers(self) -> None:
        self.logger.info("Loading SYNC managers...")

        utils.ItemManager.load()
        self.logger.info(" * Loading ItemManager... success")

        utils.MinigameDialogueManager.load()
        self.logger.info(" * Loading MinigameDialogueManager... success")

    @commands.Cog.listener("on_ready")
    async def load_async_managers(self) -> None:
        self.logger.info("Loading ASYNC managers...")

        await utils.SlashCommandMappingManager.load(self.bot)
        self.logger.info(" * Loading SlashCommandMappingManager... success")


def setup(bot: utils.Bot):
    bot.add_cog(LoadingCog(bot))
