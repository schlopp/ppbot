from discord.ext import commands, vbu

from . import utils


class NewCommandCog(vbu.Cog[utils.Bot]):
    @commands.command(
        "new",
        utils.Command,
        category=utils.CommandCategory.GETTING_STARTED,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.is_slash_command()
    async def new_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Create your very own pp!
        """
        async with utils.DatabaseWrapper() as db:
            embed = utils.Embed()

            try:
                await utils.Pp.fetch_from_user(db.conn, ctx.author.id)
            except utils.PpMissing:
                await db("INSERT INTO pps VALUES ($1)", ctx.author.id)
                embed.colour = utils.GREEN
                embed.description = f"{ctx.author.mention}, you now have a pp!"
                new_pp = True
            else:
                embed.colour = utils.RED
                embed.description = f"{ctx.author.mention}, you already have a pp!"
                new_pp = False

            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)

            if not new_pp:
                return

            embed = utils.Embed()
            embed.color = utils.PINK
            embed.title = "welcome to pp bot!!"
            embed.url = utils.MEME_URL
            embed.description = (
                "hello and welcome to the cock growing experience."
                " you've just created your very own pp,"
                " but right now it's only **0 inches** (small as fuck)"
                "\n\n"
                "to start growing ur pp,"
                f" use {utils.format_slash_command('grow')} and {utils.format_slash_command('beg')}"
                "\n\n"
                "when ur pp gets big enough,"
                f" you can go to the {utils.format_slash_command('shop')}"
                " and buy yourself some pp-growing pills."
                " these pills increase your multiplier,"
                " which makes you get more inches when using commands :)"
                "\n\n"
                "eventually you'll be able to buy some items that unlock new pp-growing commands."
                f" check {utils.format_slash_command('unlocked-commands')}"
                " to see what items unlock which commands"
            )
            await ctx.interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: utils.Bot):
    await bot.add_cog(NewCommandCog(bot))
