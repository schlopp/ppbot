import discord
from discord.ext import commands, vbu

from . import utils


class ReplyCommandCog(vbu.Cog[utils.Bot]):
    @commands.command(
        "reply",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="content",
                    type=discord.ApplicationCommandOptionType.string,
                    description="Your reply to the minigame",
                )
            ]
        ),
    )
    @commands.is_slash_command()
    async def reply_command(
        self, ctx: commands.SlashContext[utils.Bot], content: str
    ) -> None:
        """
        Only used to reply to pp bot events/minigames!
        """

        if not isinstance(ctx.channel, discord.TextChannel):
            return

        try:
            future, check = utils.ReplyManager.active_listeners[ctx.channel]
        except KeyError:
            await ctx.interaction.response.send_message(
                f"There's nothing to reply to! If you've randomly stumbled across this command, don't worry. The /reply command is only meant to be used when the bot tells you to, i.e., during a random event.",
                ephemeral=True,
            )
            return

        if check(ctx, content):
            future.set_result((ctx, content))


def setup(bot: utils.Bot):
    bot.add_cog(ReplyCommandCog(bot))
