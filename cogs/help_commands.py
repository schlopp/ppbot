from discord.ext import commands, vbu

from . import utils


class HelpCommandsCog(vbu.Cog[utils.Bot]):
    @commands.command(
        "help",
        utils.Command,
        category=utils.CommandCategory.GETTING_STARTED,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def help_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Need some help? Here you go :)
        """

        await ctx.interaction.response.send_message("no help for u")


async def setup(bot: utils.Bot):
    await bot.add_cog(HelpCommandsCog(bot))
