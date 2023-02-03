import discord
import random
from discord.ext import commands, vbu
from . import utils


class RenameCommandCog(vbu.Cog[utils.Bot]):
    @commands.command(
        "rename",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="name",
                    type=discord.ApplicationCommandOptionType.string,
                    description="Your new name",
                )
            ]
        ),
    )
    @commands.is_slash_command()
    async def rename_command(
        self, ctx: vbu.SlashContext[discord.Guild | None], name: str
    ) -> None:
        """
        Rename your big ol' Johnson
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

            if pp.name.value == name:
                raise commands.CheckFailure("Bro that's literally the same name lmao")

            pp.name.value = name
            await pp.update(db.conn)

            with utils.Embed(include_tip=True) as embed:
                embed.colour = utils.GREEN
                embed.title = (
                    random.choice(
                        [
                            "no problm",
                            "here u go",
                            "done and dusted",
                            "nice name",
                        ]
                    )
                    + " :)"
                )
                embed.description = f"{ctx.author.mention}, ur pp's name is now ~~{pp.name.start_value}~~ **{pp.name.value}**"

            if ctx.interaction.response.is_done():
                await ctx.interaction.followup.send(embed=embed)
            else:
                await ctx.interaction.response.send_message(embed=embed)


def setup(bot: utils.Bot):
    bot.add_cog(RenameCommandCog(bot))
