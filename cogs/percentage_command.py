import random
from string import ascii_letters, digits

import discord
from discord.ext import commands, vbu

from . import utils


class PercentageCommandCog(vbu.Cog[utils.Bot]):

    @commands.command(
        "percentage",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="trait",
                    type=discord.ApplicationCommandOptionType.string,
                    description="Find out what percentage [trait] you are!",
                )
            ]
        ),
    )
    @commands.is_slash_command()
    async def percentage_command(
        self, ctx: commands.SlashContext[utils.Bot], trait: str
    ) -> None:
        """
        Find out something new about yourself!
        """

        percentage = random.randint(0, 100)
        trait = utils.clean(trait)

        embed = utils.Embed()
        embed.colour = utils.GREEN
        embed.title = f"{percentage}% {trait}"
        embed.description = random.choice(
            [
                "{user} feels {percentage} {trait}",
                "{user} is {percentage} {trait}",
                "{user} is only {percentage} {trait}",
                "{user} is {percentage} {trait}",
                "{user} has {percentage} {trait} energy",
                "{user} radiates {percentage} {trait} energy",
                "{user} scores {percentage} in {trait}",
                "{user} is rated {percentage} {trait}",
                "{user} ranks {percentage} in {trait}",
                "{user} has been determined to be {percentage} {trait}",
                "According to our highly scientific calculations, {user} is {percentage} {trait}",
                "Scientists have concluded that {user} is {percentage} {trait}",
                "The results are in: {user} is {percentage} {trait}",
                "After careful analysis, {user} is {percentage} {trait}",
                "The {trait} detector says {user} is {percentage} {trait}",
                "The test says {user} is {percentage} {trait}",
                "{user} tested at {percentage} {trait}",
                "{user}'s {trait} level is {percentage}",
                "{user} contains approximately {percentage} {trait}",
                "On the {trait} scale, {user} scores {percentage}",
            ]
        ).format(user=ctx.author.mention, percentage=f"**{percentage}%**", trait=trait)
        embed.add_tip()

        await ctx.interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(PercentageCommandCog(bot))
