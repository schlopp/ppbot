import asyncio
import random
import uuid

import discord
from discord.ext import commands, vbu

from . import utils


class DonateCommandCog(vbu.Cog[utils.Bot]):
    DONATION_LIMIT = 10_000_000

    @commands.command(
        "donate",
        utils.Command,
        category=utils.CommandCategory.OTHER,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="recipiant",
                    type=discord.ApplicationCommandOptionType.user,
                    description="The recipiant of your donation",
                ),
                discord.ApplicationCommandOption(
                    name="amount",
                    type=discord.ApplicationCommandOptionType.integer,
                    description="The amount of inches u wanna donate",
                ),
            ]
        ),
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.is_slash_command()
    async def donate_command(
        self,
        ctx: commands.SlashContext[utils.Bot],
        recipiant: discord.Member | discord.User,
        amount: int,
    ) -> None:
        """
        Donate some inches to another pp!
        """
        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, "You're still busy donating!"
            ),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)

            if recipiant == ctx.author:
                raise commands.BadArgument(
                    f"{ctx.author.mention} dawg u can't donate to yourself :/"
                )

            try:
                recipiant_pp = await utils.Pp.fetch_from_user(
                    db.conn, recipiant.id, edit=True
                )
            except utils.PpMissing:
                raise utils.PpMissing(
                    f"{recipiant.mention} doesn't have a pp 🫵😂😂"
                    f" tell em to go make one with {utils.format_slash_command('new')}"
                    " and get started on the pp grind",
                    user=recipiant,
                )

            if amount < pp.size.value:
                raise utils.PpNotBigEnough(
                    f"{ctx.author.mention} your pp isn't big enough to donate that much 🫵😂😂"
                    f" you only have {utils.format_inches(pp.size.value)} lil bro"
                )

            if amount > self.DONATION_LIMIT:
                embed = utils.Embed(color=utils.RED)
                embed.description = (
                    f"{ctx.author.mention} you can't donate that much bro the limit"
                    f" is {utils.format_inches(self.DONATION_LIMIT)}"
                )

                interaction_id = uuid.uuid4().hex
                components = discord.ui.MessageComponents(
                    discord.ui.ActionRow(
                        discord.ui.Button(
                            label=f"Change amount to {utils.format_inches(self.DONATION_LIMIT, markdown=None)}",
                            custom_id=f"{interaction_id}_USE_DONATION_LIMIT",
                            style=discord.ButtonStyle.green,
                        ),
                        discord.ui.Button(
                            label=f"Cancel donation",
                            custom_id=f"{interaction_id}_CANCEL_DONATION",
                            style=discord.ButtonStyle.red,
                        ),
                    )
                )

                await ctx.interaction.response.send_message(
                    embed=embed, components=components
                )

                try:
                    interaction, action = await utils.wait_for_component_interaction(
                        self.bot,
                        interaction_id,
                        users=[ctx.author],
                        actions=["USE_DONATION_LIMIT", "CANCEL_DONATION"],
                        timeout=10,
                    )
                except asyncio.TimeoutError:
                    await ctx.interaction.edit_original_message(
                        embed=utils.Embed.as_timeout("Donation cancelled"),
                        components=components.disable_components(),
                    )
                    return

            # pp.grow_with_multipliers(
            #     random.randint(1, 15),
            #     voted=await pp.has_voted(),
            # )
            # await pp.update(db.conn)

            embed = utils.Embed()
            embed.colour = utils.GREEN
            embed.description = (
                f"{ctx.author.mention} u tried donating to {recipiant.mention}"
            )

            await ctx.interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(DonateCommandCog(bot))
