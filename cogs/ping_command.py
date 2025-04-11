import random
import time
from functools import partial

import discord
from discord.ext import commands, vbu

from . import utils


class PingCommandCog(vbu.Cog[utils.Bot]):

    @commands.command(
        "ping",
        utils.Command,
        category=utils.CommandCategory.OTHER,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def ping_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Check pp bot's reponse time
        """

        embed = utils.Embed()
        embed.title = "Ping... 🏓 "

        start = time.time()

        await ctx.interaction.response.send_message(embed=embed)

        rest_api_ping = time.time() - start

        format_time = partial(utils.format_time, smallest_unit="millisecond")

        embed.title = "🏓 Pong!"
        embed.description = (
            f"Discord Rest API ping: **{format_time(rest_api_ping)}**"
            f"\nDiscord Gateway avg. ping: **{format_time(self.bot.latency)}**"
            f"\n {utils.format_iterable(f'Shard #{shard_id}: **{format_time(latency)}**' for shard_id, latency in self.bot.latencies)}"
        )
        self.bot.latency

        await ctx.interaction.edit_original_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(PingCommandCog(bot))
