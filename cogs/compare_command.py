import asyncio
import random
import uuid
from typing import Literal, overload

import discord
from discord.ext import commands, vbu

from . import utils


class CompareCommandCog(vbu.Cog[utils.Bot]):
    @overload
    def compare_amounts(
        self,
        author: discord.Member | discord.User,
        opponent: discord.Member | discord.User,
        author_amount: int,
        opponent_amount: int,
        *,
        with_ratio: Literal[False] = False,
    ) -> tuple[
        discord.Member | discord.User, discord.Member | discord.User, int, str
    ]: ...

    @overload
    def compare_amounts(
        self,
        author: discord.Member | discord.User,
        opponent: discord.Member | discord.User,
        author_amount: int,
        opponent_amount: int,
        *,
        with_ratio: Literal[True],
    ) -> tuple[
        discord.Member | discord.User, discord.Member | discord.User, int, str, float
    ]: ...

    def compare_amounts(
        self,
        author: discord.Member | discord.User,
        opponent: discord.Member | discord.User,
        author_amount: int,
        opponent_amount: int,
        *,
        with_ratio: bool = False,
    ) -> (
        tuple[discord.Member | discord.User, discord.Member | discord.User, int, str]
        | tuple[
            discord.Member | discord.User,
            discord.Member | discord.User,
            int,
            str,
            float,
        ]
    ):
        """
        Returns tuple[winner: discord.Member | discord.User, loser: discord.Member | discord.User, difference: int, percentage_difference: str]
        """

        if author_amount > opponent_amount:
            winner = author
            loser = opponent
        else:
            winner = opponent
            loser = author

        difference = abs(author_amount - opponent_amount)

        try:
            ratio = max(author_amount, opponent_amount) / min(
                author_amount, opponent_amount
            )

            percentage_difference_raw = ratio * 100 - 100
            percentage_difference = f"{percentage_difference_raw:{'.1f' if percentage_difference_raw < 100 else '.0f'}}%"
        except ZeroDivisionError:
            ratio = float("inf")
            percentage_difference = "literally infinity%"

        if with_ratio:
            return (
                winner,
                loser,
                difference,
                percentage_difference,
                ratio,
            )

        return winner, loser, difference, percentage_difference

    @commands.command(
        "compare",
        utils.Command,
        category=utils.CommandCategory.STATS,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="opponent",
                    type=discord.ApplicationCommandOptionType.user,
                    description="Whoever's pp you want to compare with",
                )
            ]
        ),
    )
    @commands.is_slash_command()
    async def compare_command(
        self, ctx: commands.SlashContext[utils.Bot], opponent: discord.Member
    ) -> None:
        """
        Compare your pp with someone else in the ultimate pp showdown
        """

        opponent = opponent

        if opponent == ctx.author:
            raise commands.BadArgument("You can't compare against yourself silly!")

        async with utils.DatabaseWrapper() as db:
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id)

            try:
                opponent_pp = await utils.Pp.fetch_from_user(db.conn, opponent.id)
            except utils.PpMissing:
                raise utils.PpMissing(
                    f"{opponent.mention} ain't got a pp :(", user=opponent
                )

            inventory = await utils.InventoryItem.fetch(
                db.conn,
                {"user_id": ctx.author.id},
                fetch_multiple_rows=True,
            )
            item_count = 0
            for item in inventory:
                item_count += item.amount.value

            opponent_inventory = await utils.InventoryItem.fetch(
                db.conn,
                {"user_id": opponent.id},
                fetch_multiple_rows=True,
            )
            opponent_item_count = 0
            for item in opponent_inventory:
                opponent_item_count += item.amount.value

        display_name = utils.clean(ctx.author.display_name)
        opponent_display_name = utils.clean(opponent.display_name)

        embed = utils.Embed()
        embed.title = f"{display_name} VS. {opponent_display_name}"

        segments: list[tuple[str, str, str]] = []

        # comparing size
        winner, loser, difference, percentage_difference = self.compare_amounts(
            ctx.author, opponent, pp.size.value, opponent_pp.size.value
        )

        match utils.find_nearest_number(utils.REAL_LIFE_COMPARISONS, difference):
            case nearest_number, -1:
                comparison_text = f"{utils.format_inches(difference - nearest_number)} bigger than"
            case nearest_number, 0:
                comparison_text = f"the same size as"
            case nearest_number, _:
                comparison_text = f"{utils.format_inches(nearest_number - difference)} smaller than"

        segments.append(
            (
                "size",
                f"{winner.mention}'s pp is {utils.format_inches(difference)} bigger than {loser.mention}'s! `{percentage_difference} bigger`",
                f"That difference is {comparison_text} {utils.REAL_LIFE_COMPARISONS[nearest_number]}",
            )
        )

        # Comparing multiplier
        winner, loser, difference, percentage_difference, ratio = self.compare_amounts(
            ctx.author,
            opponent,
            pp.multiplier.value,
            opponent_pp.multiplier.value,
            with_ratio=True,
        )
        loser_display_name = (
            display_name if loser == ctx.author else opponent_display_name
        )

        segments.append(
            (
                "multiplier",
                f"{winner.mention}'s multiplier is **{ratio:{'.1f' if ratio < 100 else '.0f'}}x**"
                f" bigger than {loser.mention}'s! `{percentage_difference} bigger`",
                (
                    f"(NOT INCLUDING BOOSTS) {loser_display_name} will have to take"
                    f" {utils.format_int(difference)} pills to make up for that difference"
                ),
            )
        )

        # Comparing item count
        winner, loser, difference, percentage_difference = self.compare_amounts(
            ctx.author, opponent, item_count, opponent_item_count
        )

        if winner == ctx.author:
            winner_display_name = display_name
            winner_item_count = item_count
        else:
            winner_display_name = opponent_display_name
            winner_item_count = opponent_item_count

        comment = utils.ITEM_COUNT_COMMENTS[
            utils.find_nearest_number(utils.ITEM_COUNT_COMMENTS, winner_item_count)[0]
        ][1]

        segments.append(
            (
                "items",
                f"{winner.mention} has {utils.format_int(difference)} more items than {loser.mention}! `{percentage_difference} more`",
                (
                    f"{winner_display_name} has a total of"
                    f" {utils.format_int(winner_item_count)} items. {comment}"
                ),
            )
        )

        for title, comparison, subtext in segments:
            embed.add_field(
                name=title.upper(), value=f"{comparison}\n-# {subtext}", inline=False
            )

        await ctx.interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(CompareCommandCog(bot))
