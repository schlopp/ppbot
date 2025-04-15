import random

from discord.ext import commands, vbu

from . import utils


class GrowCommandCog(vbu.Cog[utils.Bot]):
    @commands.command(
        "grow",
        utils.Command,
        category=utils.CommandCategory.GROWING_PP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.cooldown(1, 20, commands.BucketType.user)
    @commands.is_slash_command()
    async def grow_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Grow your pp to get more inches!
        """
        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, "You're still busy with the grow command!"
            ),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)

            pp.grow_with_multipliers(
                random.randint(1, 15),
                voted=await pp.has_voted(),
            )
            await pp.update(db.conn)

            embed = utils.Embed()
            embed.colour = utils.GREEN
            embed.description = (
                f"{ctx.author.mention}, ur pp grew {pp.format_growth()}!"
            )
            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(GrowCommandCog(bot))
