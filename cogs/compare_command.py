import asyncio
import random
import uuid
from typing import Literal, overload

import discord
from discord.ext import commands, vbu

from . import utils


class CompareCommandCog(vbu.Cog[utils.Bot]):
    BOOST_DESCRIPTIONS: dict[str, str] = {
        "voter": f"voting on [**top.gg**]({utils.VOTE_URL})",
        "weekend": "for playing during the weekend :)",
        "pp_bot_channel": "for being in a channel named after pp bot <:ppHappy:902894208703156257>",
    }

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

        ratio = max(author_amount, opponent_amount) / min(
            author_amount, opponent_amount
        )

        percentage_difference_raw = ratio * 100 - 100
        percentage_difference = f"{percentage_difference_raw:{'.1f' if percentage_difference_raw < 100 else '.0f'}}%"

        if with_ratio:
            return (
                winner,
                loser,
                difference,
                percentage_difference,
                ratio,
            )

        return winner, loser, difference, percentage_difference

    def _component_factory(
        self, *, current_page_id: Literal["SHOW", "INVENTORY", "UNLOCKED_COMMANDS"]
    ) -> tuple[str, discord.ui.MessageComponents]:
        """Returns `(interaction_id: str, components: discord.ui.MessageComponents)`"""
        interaction_id = uuid.uuid4().hex
        buttons: dict[str, discord.ui.Button] = {
            "SHOW": discord.ui.Button(label="Show", custom_id=f"{interaction_id}_SHOW"),
            "INVENTORY": discord.ui.Button(
                label="Inventory", custom_id=f"{interaction_id}_INVENTORY"
            ),
            "UNLOCKED_COMMANDS": discord.ui.Button(
                label="Unlocked Commands",
                custom_id=f"{interaction_id}_UNLOCKED_COMMANDS",
            ),
            "BUFFS": discord.ui.Button(
                label="Active Buffs (COMING SOON)", disabled=True
            ),
        }
        buttons[current_page_id].style = discord.ButtonStyle.blurple
        buttons[current_page_id].disabled = True
        return interaction_id, discord.ui.MessageComponents(
            discord.ui.ActionRow(*buttons.values())
        )

    async def _show_embed_factory(
        self, member: discord.Member | discord.User, pp: utils.Pp, *, is_author: bool
    ) -> utils.Embed:
        display_name = utils.clean(member.display_name)

        embed = utils.Embed()
        embed.colour = utils.BLUE
        embed.title = utils.limit_text(f"{pp.name.value} ({display_name}'s pp)", 256)
        embed.description = f"8{'=' * min(pp.size.value // 50, 1000)}D"

        voted = await pp.has_voted()
        full_multiplier, boosts, total_boost = pp.get_full_multiplier(voted=voted)

        if total_boost != 1:
            multiplier_display = (
                f"~~{utils.format_int(pp.multiplier.value)}x~~"
                f" **{utils.format_int(full_multiplier)}**x multiplier"
                f" [**[+{int(total_boost * 100) - 100}%]**]({utils.MEME_URL})"
            )
        else:
            multiplier_display = f"**{utils.format_int(full_multiplier)}**x multiplier"

        boost_subdisplays: list[str] = []

        if not voted:
            boost_subdisplays.append(
                f"vote on [**top.gg**]({utils.VOTE_URL}) for an extra **{utils.BoostType.VOTE.percentage}% boost!**"
            )
            if not is_author:
                boost_subdisplays[-1] = (
                    f"tell {member.mention} to " + boost_subdisplays[-1]
                )

        for boost, boost_percentage in boosts.items():
            boost_subdisplays.append(
                f"**[{boost} bonus:]({utils.MEME_URL}) +{int(boost_percentage * 100)}%**"
                f" for {self.BOOST_DESCRIPTIONS.get(boost, '???')}"
            )

        if boost_subdisplays:
            boost_display = utils.format_iterable(boost_subdisplays, joiner=" ╰ ")
            multiplier_display += f"\n{boost_display}"

        embed.add_field(
            name="stats",
            value=utils.format_iterable(
                [
                    f"**{utils.format_int(pp.size.value)}** inches",
                    multiplier_display,
                ]
            ),
        )

        other_stats: list[str] = []

        # easter egg xddd
        easter_egg_stats = [
            f"{"you smell" if is_author else f"{member.mention} smells"} [**REALLY**]({utils.MEME_URL}) bad",
            f"{"your" if is_author else f"{member.mention}'s"} parents [**dont love you**]({utils.MEME_URL})",
            f"{"you've" if is_author else f"{member.mention} has"} taken [**3 showers**]({utils.MEME_URL}) this year",
            f"{"you" if is_author else member.mention} will [**never find love**]({utils.MEME_URL})",
        ]

        if random.random() > 0.05:
            other_stats.append(random.choice(easter_egg_stats))

        if pp.digging_depth.value > 0:
            other_stats.append(
                f"{"You've" if is_author else f"{member.mention} has"} dug"
                f" **{utils.format_int(pp.digging_depth.value)} feet** deep"
            )

        if other_stats:
            embed.add_field(
                name="and some more stats",
                value=utils.format_iterable(other_stats),
            )

        match utils.find_nearest_number(utils.REAL_LIFE_COMPARISONS, pp.size.value):
            case nearest_number, -1:
                comparison_text = f"{utils.format_int(pp.size.value - nearest_number)} inches bigger than"
            case nearest_number, 0:
                comparison_text = f"the same size as"
            case nearest_number, _:
                comparison_text = f"{utils.format_int(nearest_number - pp.size.value)} inches smaller than"

        embed.set_footer(
            text=(
                f"{"Your" if is_author else f"{display_name}'s"} pp is"
                f" {comparison_text} {utils.REAL_LIFE_COMPARISONS[nearest_number]}"
            )
        )

        return embed

    def _inventory_embed_factory(
        self,
        member: discord.Member | discord.User,
        inventory: list[utils.InventoryItem],
        is_author: bool,
    ) -> utils.Embed:
        display_name = utils.clean(member.display_name)

        embed = utils.Embed()
        embed.colour = utils.BLUE
        embed.title = f"{display_name}'s inventory"

        categories: dict[str, list[utils.InventoryItem]] = {
            utils.ToolItem.category_name: [],
            utils.BuffItem.category_name: [],
            utils.UselessItem.category_name: [],
            utils.LegacyItem.category_name: [],
        }
        sorted_inventory = sorted(
            inventory, key=lambda inv_item: inv_item.amount.value, reverse=True
        )

        item_count = 0

        for inv_item in sorted_inventory:
            item_count += inv_item.amount.value
            try:
                categories[inv_item.item.category_name].append(inv_item)
            except KeyError:
                categories[inv_item.item.category_name] = [inv_item]

        # Used to add a lil more space between the fields
        zero_width_character = "​"
        em_space_character = " "

        for category_name, inv_items in categories.items():
            if not inv_items:
                continue
            embed.add_field(
                name=category_name,
                value="\n".join(
                    f"**{utils.format_int(inv_item.amount.value)}**x "
                    + (
                        inv_item.item.name
                        if inv_item.amount.value == 1
                        else inv_item.item.plural
                    )
                    + em_space_character * 2
                    + zero_width_character
                    for inv_item in inv_items
                ),
            )

        comment = utils.ITEM_COUNT_COMMENTS[
            utils.find_nearest_number(utils.ITEM_COUNT_COMMENTS, item_count)[0]
        ][0 if is_author else 1]
        embed.set_footer(
            text=f"{utils.format_int(item_count)} items in total. {comment}"
        )

        return embed

    def _unlocked_commands_embed_factory(
        self,
        member: discord.Member | discord.User,
        inventory: list[utils.InventoryItem],
    ) -> utils.Embed:
        display_name = utils.clean(member.display_name)

        embed = utils.Embed()
        embed.colour = utils.BLUE
        embed.title = f"{display_name}'s unlocked commands"

        unlocked_commands = [
            inv_item.item
            for inv_item in inventory
            if isinstance(inv_item.item, utils.ToolItem)
        ]

        locked_commands = [
            tool
            for tool in utils.ItemManager.tools.values()
            if tool not in unlocked_commands
        ]

        unlocked_commands.sort(key=lambda tool: tool.price)
        locked_commands.sort(key=lambda tool: tool.price)

        categories = {
            "🔓 UNLOCKED": unlocked_commands,
            "🔒 LOCKED": locked_commands,
        }

        progress_bar = f"[{'▮' * len(unlocked_commands)}{'▯' * len(locked_commands)}]"

        embed.description = (
            f"**`{progress_bar} ({len(unlocked_commands)}/"
            f"{len(unlocked_commands) + len(locked_commands)} unlocked)`**"
            "\n\n**What are locked commands?**\n Locked commands are commands that require a"
            " specific item to unlock.\n- These items can be bought in the"
            f" {utils.format_slash_command('shop')}"
            # f" unlocked)`**\n\nuse {utils.format_slash_command('buy')} to unlock more items :))"
            # f"\n& check out {utils.format_slash_command('help')}  to see all the other commands!"
        )

        # Used to add a lil more space between the fields
        zero_width_character = "​"
        em_space_character = " "

        for category, tools in categories.items():
            if not tools:
                continue
            embed.add_field(
                name=category,
                value="\n".join(
                    f"{tool.associated_command_link} (from **{tool.name}**)"
                    + em_space_character * 2
                    + zero_width_character
                    for tool in tools
                ),
            )

        return embed

    async def handle_tabs(
        self,
        ctx: commands.SlashContext[utils.Bot],
        member: discord.Member | discord.User,
        interaction_id: str,
        components: discord.ui.MessageComponents,
        pp: utils.Pp | None = None,
        inventory: list[utils.InventoryItem] | None = None,
    ) -> None:
        embed = None
        while True:
            try:
                (
                    component_interaction,
                    action,
                ) = await utils.wait_for_component_interaction(
                    self.bot, interaction_id, users=[ctx.author], timeout=180
                )
            except asyncio.TimeoutError:
                components.disable_components()
                await ctx.interaction.edit_original_message(components=components)
                break

            if action == "INVENTORY":
                if inventory is None:
                    async with utils.DatabaseWrapper() as db:
                        inventory = await utils.InventoryItem.fetch(
                            db.conn,
                            {"user_id": member.id},
                            fetch_multiple_rows=True,
                        )
                embed = self._inventory_embed_factory(
                    member, inventory, is_author=ctx.author == member
                )
                interaction_id, components = self._component_factory(
                    current_page_id="INVENTORY"
                )
            elif action == "SHOW":
                if pp is None:
                    async with utils.DatabaseWrapper() as db:
                        try:
                            pp = await utils.Pp.fetch_from_user(db.conn, member.id)
                        except utils.PpMissing:
                            if member == ctx.author:
                                raise
                            raise utils.PpMissing(
                                f"{member.mention} ain't got a pp :(", user=member
                            )

                embed = await self._show_embed_factory(
                    member, pp, is_author=ctx.author == member
                )
                interaction_id, components = self._component_factory(
                    current_page_id="SHOW"
                )
            elif action == "UNLOCKED_COMMANDS":
                if inventory is None:
                    async with utils.DatabaseWrapper() as db:
                        inventory = await utils.InventoryItem.fetch(
                            db.conn,
                            {"user_id": ctx.author.id},
                            fetch_multiple_rows=True,
                        )
                embed = self._unlocked_commands_embed_factory(member, inventory)
                interaction_id, components = self._component_factory(
                    current_page_id="UNLOCKED_COMMANDS"
                )

            await component_interaction.response.edit_message(
                embed=embed, components=components
            )

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
                comparison_text = f"{utils.format_int(difference - nearest_number)} inches bigger than"
            case nearest_number, 0:
                comparison_text = f"the same size as"
            case nearest_number, _:
                comparison_text = f"{utils.format_int(nearest_number - difference)} inches smaller than"

        segments.append(
            (
                "size",
                f"{winner.mention}'s pp is {utils.format_inches(difference)} bigger than {loser.mention}'s! `{percentage_difference} bigger`",
                f"That's difference is {comparison_text} {utils.REAL_LIFE_COMPARISONS[nearest_number]}",
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
                f"(NOT INCLUDING BOOSTS) {loser_display_name} will have to take {difference} pills to make up for that difference",
            )
        )

        for title, comparison, subtext in segments:
            embed.add_field(
                name=title.upper(), value=f"{comparison}\n-# {subtext}", inline=False
            )

        await ctx.interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(CompareCommandCog(bot))
