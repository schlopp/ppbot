import textwrap

import discord
from discord.ext import commands, vbu


class CommandHandlerCog(vbu.Cog):
    EMBED_DESCRIPTION = textwrap.dedent(
        """
    # The largest update in pp bot history is coming...

    In a few hours, the biggest pp bot update **ever** will be released.

    - All commands will **run faster** and **look better**
    - All commands have been reworked to be **user-friendly**
    - **BRAND NEW** `/casino`
    - **BRAND NEW MINIGAMES** FOR `/beg` `/fish` `/hunt`
    - And **SO MUCH MORE**

    ‎ 
    [**Join our Discord**](https://discord.gg/ppbot) and be the first to know when the update launches!!

    -# Thank you all so much for the support I've received over the last few years. I haven't updated pp bot in years but from now on updates will be regular and on a monthly basis. - schlöpp

    [**TRIPLE MULTIPLIER EVENT AND HUGE GIVEAWAY**](https://discord.gg) **TO CELEBRATE THE NEW UPDATE!**
    """.strip(
            "\n"
        )
    )
    IMAGE_URL = "https://media.discordapp.net/attachments/959818177926275082/1382715249098231920/ppbot_update1.png"

    async def respond(
        self, ctx: commands.Context[vbu.Bot] | commands.SlashContext[vbu.Bot]
    ):
        embed = discord.Embed()
        embed.set_author(name="THE GREAT PP BOT REVAMP")
        embed.description = self.EMBED_DESCRIPTION
        embed.colour = discord.Colour(15418782)
        await ctx.send(
            "im so sorry but we can't run that command right now :(", embed=embed
        )
        embed.set_image(url=self.IMAGE_URL)

    @vbu.Cog.listener("command")
    async def on_command(
        self, ctx: commands.Context[vbu.Bot] | commands.SlashContext[vbu.Bot]
    ):
        await self.respond(ctx)

    @vbu.Cog.listener("on_command_error")
    async def on_command_error(
        self,
        ctx: commands.Context[vbu.Bot] | commands.SlashContext[vbu.Bot],
        command_error: commands.CommandError,
    ):
        print(1)
        await self.respond(ctx)


async def setup(bot: vbu.Bot):
    x = CommandHandlerCog(bot)
    await bot.add_cog(x)
