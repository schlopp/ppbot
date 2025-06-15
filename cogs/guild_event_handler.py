import textwrap

import discord
from discord.ext import commands, vbu

from . import utils


class GuildEventHandlerCog(vbu.Cog[utils.Bot]):

    @vbu.Cog.listener("on_guild_join")
    async def send_introduction(self, guild: discord.Guild) -> None:
        embed = utils.Embed(color=utils.PINK)
        embed.description = textwrap.dedent(
            f"""
            # pp bot has joined the game

            what's up fuckers? it's me, pp bot <:ppevil:871396299830861884>"""
            " I'm here to bless you all with a HUGE PP."
            f" **Type {utils.format_slash_command("new")} to get started**"
            f""" and have fun growing ur pp!!

            -# need some help? just use {utils.format_slash_command("help")} lil bro
            """.strip(
                "\n"
            )
        )

        for channel in guild.channels:
            if not isinstance(channel, discord.TextChannel):
                continue
            if not channel.permissions_for(guild.me).send_messages:
                continue

            await channel.send(embed=embed)
            return


async def setup(bot: utils.Bot):
    await bot.add_cog(GuildEventHandlerCog(bot))
