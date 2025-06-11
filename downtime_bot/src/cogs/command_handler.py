from discord.ext import commands, vbu


class CommandHandlerCog(vbu.Cog):
    @vbu.Cog.listener("command")
    async def on_command(
        self, ctx: commands.Context[vbu.Bot] | commands.SlashContext[vbu.Bot]
    ):
        await ctx.send(repr(ctx))


async def setup(bot: vbu.Bot):
    x = CommandHandlerCog(bot)
    await bot.add_cog(x)
