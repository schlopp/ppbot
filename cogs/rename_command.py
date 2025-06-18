import random
from string import ascii_letters, digits

import discord
from discord.ext import commands, vbu

from . import utils


class RenameCommandCog(vbu.Cog[utils.Bot]):
    MAX_NAME_LENGTH = 32
    VALID_SPECIAL_CHARACTERS = "_.,-|/();:'\"!?^& "
    VALID_CHARACTERS = ascii_letters + digits + VALID_SPECIAL_CHARACTERS

    @commands.command(
        "rename",
        utils.Command,
        category=utils.CommandCategory.STATS,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="name",
                    type=discord.ApplicationCommandOptionType.string,
                    description="Give your pp a brand new name",
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

            if len(name) > self.MAX_NAME_LENGTH:
                raise commands.BadArgument(
                    f"That name is {len(name)} characters long,"
                    f" but the max is {self.MAX_NAME_LENGTH}"
                )

            if name.startswith(tuple("_-")) or name.endswith(tuple("_-")):
                raise commands.BadArgument(
                    "Sorry bro but ur name can't start or end with"
                    " an underscore `(_)` or a dash `(-)`"
                )

            if not all(char in self.VALID_CHARACTERS for char in name):
                raise commands.BadArgument(
                    "Sorry bro but ur name can only contain uppercase letters `(A-Z)`,"
                    " lowercase letters `(a-z)`, numbers `(0-9)` and these special characters: "
                    + " ".join(f"`{char}`" for char in self.VALID_SPECIAL_CHARACTERS)
                )

            if pp.name.value == name:
                raise commands.BadArgument("Bro that's literally the same name lmao")

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
