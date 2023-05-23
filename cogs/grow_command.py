import discord
import random
from discord.ext import commands, vbu
from . import utils


class GrowCommandCog(vbu.Cog[utils.Bot]):
    @commands.command(
        "grow",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.is_slash_command()
    async def grow_command(self, ctx: vbu.SlashContext[discord.Guild | None]) -> None:
        """
        Grow your pp to get more inches!
        """
        async with self.bot.database() as db, db.conn.transaction():
            try:
                pp = await utils.Pp.fetch(
                    db.conn,
                    {"user_id": ctx.author.id},
                    lock=utils.RowLevelLockMode.FOR_UPDATE,
                )
            except utils.RecordNotFoundError:
                raise commands.CheckFailure("You don't have a pp!")

            pp.grow(random.randint(*utils.command_settings["grow"]["growth_rate"]))
            await pp.update(db.conn)

            embed = utils.Embed()
            embed.colour = utils.GREEN
            embed.description = f"{ctx.author.mention}, ur pp grew {pp.format_growth(markdown=utils.MarkdownFormat.BOLD_BLUE)}"
            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)


def setup(bot: utils.Bot):
    bot.add_cog(GrowCommandCog(bot))
