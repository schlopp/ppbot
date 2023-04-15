import asyncio

import discord
from discord.ext import commands, vbu

from . import utils


class NewCommandCog(vbu.Cog[utils.Bot]):
    @commands.command(
        "new",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.is_slash_command()
    async def grow_command(self, ctx: vbu.SlashContext[discord.Guild | None]) -> None:
        """
        Create your very own pp!
        """
        async with self.bot.database() as db:
            embed = utils.Embed()
            try:
                await utils.Pp.fetch(
                    db.conn,
                    {"user_id": ctx.author.id},
                )
            except utils.RecordNotFoundError:
                await db("INSERT INTO pps VALUES ($1)", ctx.author.id)
                embed.colour = utils.GREEN
                embed.description = f"{ctx.author.mention}, you now have a pp!"
            else:
                embed.colour = utils.RED
                embed.description = f"{ctx.author.mention}, you already have a pp!"

            await ctx.interaction.response.send_message(embed=embed)


def setup(bot: utils.Bot):
    bot.add_cog(NewCommandCog(bot))