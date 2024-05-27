import random

import discord
from discord.ext import commands, vbu

from . import utils


class RenameCommandCog(vbu.Cog[utils.Bot]):
    MAX_NAME_LENGTH = 32

    @commands.command(
        "rename",
        utils.Command,
        category=utils.CommandCategory.STATS,
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
        self, ctx: commands.SlashContext[utils.Bot], name: str
    ) -> None:
        """
        Rename your big ol' Johnson
        """
        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, "You're still busy renaming your pp!"
            ),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)

            name = utils.clean(name)

            if len(name) > self.MAX_NAME_LENGTH:
                raise commands.CheckFailure(
                    f"That name is {len(name)} characters long,"
                    f" but the max is {self.MAX_NAME_LENGTH}"
                )

            if pp.name.value == name:
                raise commands.CheckFailure("Bro that's literally the same name lmao")

            pp.name.value = name
            await pp.update(db.conn)

            embed = utils.Embed()
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
            embed.description = (
                f"{ctx.author.mention}, ur pp's name is now ~~{pp.name.start_value}~~"
                f" **{pp.name.value}**"
            )
            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(RenameCommandCog(bot))
