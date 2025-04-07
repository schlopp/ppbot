import asyncio
import random
import uuid

import discord
from discord.ext import commands, vbu

from . import utils


class DonateCommandCog(vbu.Cog[utils.Bot]):
    DONATION_LIMIT = 1000

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
    # @commands.cooldown(1, 30, commands.BucketType.user)
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
                recipiant_pp = await utils.Pp.fetch_from_user(db.conn, recipiant.id)
            except utils.PpMissing:
                raise utils.PpMissing(
                    f"{recipiant.mention} doesn't have a pp 🫵😂😂"
                    f" tell em to go make one with {utils.format_slash_command('new')}"
                    " and get started on the pp grind",
                    user=recipiant,
                )

            if amount > pp.size.value:
                raise utils.PpNotBigEnough(
                    f"{ctx.author.mention} your pp isn't big enough to donate that much 🫵😂😂"
                    f" you only have {utils.format_inches(pp.size.value)} lil bro"
                )

            relevant_received_donation_sum = (
                await utils.Donation.fetch_relevant_received_donation_sum(
                    db.conn, recipiant.id
                )
            )

            if relevant_received_donation_sum >= self.DONATION_LIMIT:
                raise commands.CheckFailure(
                    f"{recipiant.mention} has already hit the daily donation limit"
                    f"of {utils.format_inches(self.DONATION_LIMIT)}"
                )

            interaction_id = uuid.uuid4().hex

            if amount + relevant_received_donation_sum > self.DONATION_LIMIT:
                embed = utils.Embed(color=utils.RED)
                embed.description = (
                    f"{ctx.author.mention} you can't donate that much to {recipiant.mention} bro the limit"
                    f" is {utils.format_inches(self.DONATION_LIMIT)}"
                )

                if relevant_received_donation_sum:
                    embed.description += f" and they already received {utils.format_inches(relevant_received_donation_sum)}"

                components = discord.ui.MessageComponents(
                    discord.ui.ActionRow(
                        discord.ui.Button(
                            label=f"Change amount to {utils.format_inches(self.DONATION_LIMIT - relevant_received_donation_sum, markdown=None)}",
                            custom_id=f"{interaction_id}_DONATE",
                            style=discord.ButtonStyle.green,
                        ),
                        discord.ui.Button(
                            label=f"Cancel donation",
                            custom_id=f"{interaction_id}_CANCEL_DONATION",
                            style=discord.ButtonStyle.red,
                        ),
                    )
                )

                amount = self.DONATION_LIMIT - relevant_received_donation_sum

            else:
                embed = utils.Embed()
                embed.description = (
                    f"{ctx.author.mention} are u sure you want to donate"
                    f" {utils.format_inches(amount)} to {recipiant.mention}?"
                )

                components = discord.ui.MessageComponents(
                    discord.ui.ActionRow(
                        discord.ui.Button(
                            label=f"yes!!",
                            custom_id=f"{interaction_id}_DONATE",
                            style=discord.ButtonStyle.green,
                        ),
                        discord.ui.Button(
                            label=f"no",
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
                    actions=["DONATE", "CANCEL_DONATION"],
                    timeout=10,
                )
            except asyncio.TimeoutError:
                await ctx.interaction.edit_original_message(
                    embed=utils.Embed.as_timeout("Donation cancelled"),
                    components=components.disable_components(),
                )
                return

            if action == "CANCEL_DONATION":
                embed = utils.Embed(color=utils.RED)
                embed.title = "Donation cancelled"
                embed.description = (
                    f"I guess {ctx.author.mention} really hates {recipiant.mention}"
                )
                await interaction.response.edit_message(embed=embed, components=None)
                return

            # Fetch the recipiant pp again with edit=true
            # Do this only now so that the recipiant isn't locked from using
            # other commands while acceping a donation
            async with (
                utils.DatabaseWrapper() as recipiant_db,
                recipiant_db.conn.transaction(),
                utils.DatabaseTimeoutManager.notify(
                    recipiant.id,
                    "You're receiving a donation right now and it's still being processed! Please try again!!",
                ),
            ):
                try:
                    recipiant_pp = await utils.Pp.fetch_from_user(
                        recipiant_db.conn, recipiant.id, edit=True
                    )
                except utils.DatabaseTimeout:
                    await ctx.interaction.edit_original_message(
                        components=components.disable_components()
                    )
                    raise commands.CheckFailure(
                        f"{recipiant.mention} seems to be busy right now! Try donating another time :)"
                    )

                await utils.Donation.register(
                    db.conn, recipiant.id, ctx.author.id, amount
                )

                pp.size.value -= amount
                recipiant_pp.size.value += amount
                await pp.update(db.conn)
                await recipiant_pp.update(recipiant_db.conn)

            embed = utils.Embed(color=utils.GREEN)
            embed.title = "Donation successful!"
            embed.description = (
                f"u successfully donated {utils.format_inches(amount)} to {recipiant}"
                f"\n\n {ctx.author.mention} now has {utils.format_inches(pp.size.value)}"
                f"\n {recipiant.mention} now has {utils.format_inches(recipiant_pp.size.value)}"
            )

            await interaction.response.edit_message(embed=embed, components=None)


async def setup(bot: utils.Bot):
    await bot.add_cog(DonateCommandCog(bot))
