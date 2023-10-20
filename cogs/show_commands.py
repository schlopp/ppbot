import asyncio
import uuid
from typing import Literal

import discord
from discord.ext import commands, vbu

from . import utils


class ShowCommandsCog(vbu.Cog[utils.Bot]):
    REAL_LIFE_COMPARISONS = {
        0: "your IRL pp",
        60: "the average door",
        4_133: "a football field",
        11_800: "the Eiffel Tower",
        14_519: "the depth of the ocean",
        15_000: "the Empire State Building",
        145_200: "the depth of the ocean",
        348_385: "Mount Everest",
        434_412: "the Mariana Trench",
        15_157_486_080: "the distance from the earth to the moon",
        5_984_252_000_000: "the distance from the earth to THE SUN",
    }
    ITEM_COUNT_COMMENTS = {
        0: "r u poor?",
        1: "Not much bro",
        5: "You must be new here",
        10: "You're getting there",
        20: "Not bad",
        100: "That's pretty good",
        200: "You're either rich, or don't know how to spend your inches wisely",
        500: "God DAMN",
        1000: "You must be a collector or sum",
        5000: "Jesus fucking christ man",
        10_000: "You use this bot way too fucking much",
        20_000: "Are you mentally OK? Do u need a hug??",
        100_000: "Dude just give up this is too much",
        1_000_000: "Okay. You win. I give up. I fucking quit. You win the game. Fuck you.",
    }

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

    def _show_embed_factory(
        self,
        member: discord.Member | discord.User,
        pp: utils.Pp,
    ) -> utils.Embed:
        embed = utils.Embed()
        embed.colour = utils.BLUE
        embed.title = utils.limit_text(
            f"{pp.name.value} ({utils.clean(member.display_name)}'s pp)", 256
        )
        embed.description = f"8{'=' * min(pp.size.value // 50, 1000)}D"

        embed.add_field(
            name="stats",
            value=utils.format_iterable(
                [
                    f"**{utils.format_int(pp.size.value)}** inches",
                    f"**{utils.format_int(pp.multiplier.value)}**x multiplier",
                ]
            ),
        )

        match utils.find_nearest_number(self.REAL_LIFE_COMPARISONS, pp.size.value):
            case nearest_number, -1:
                comparison_text = f"{utils.format_int(pp.size.value - nearest_number)} inches bigger than"
            case nearest_number, 0:
                comparison_text = f"the same size as"
            case nearest_number, _:
                comparison_text = f"{utils.format_int(nearest_number - pp.size.value)} inches smaller than"

        embed.set_footer(
            text=f"Your pp is {comparison_text} {self.REAL_LIFE_COMPARISONS[nearest_number]}"
        )

        return embed

    def _inventory_embed_factory(
        self,
        member: discord.Member | discord.User,
        inventory: list[utils.InventoryItem],
    ) -> utils.Embed:
        embed = utils.Embed()
        embed.colour = utils.BLUE
        embed.title = f"{utils.clean(member.display_name)}'s inventory"

        categories: dict[str, list[utils.InventoryItem]] = {
            utils.ToolItem.category_name: [],
            utils.BuffItem.category_name: [],
            utils.UselessItem.category_name: [],
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
                    f"**{utils.format_int(inv_item.amount.value)}**x {inv_item.item.name}"
                    + em_space_character * 2
                    + zero_width_character
                    for inv_item in inv_items
                ),
            )

        comment = self.ITEM_COUNT_COMMENTS[
            utils.find_nearest_number(self.ITEM_COUNT_COMMENTS, item_count)[0]
        ]
        embed.set_footer(
            text=f"{utils.format_int(item_count)} items in total. {comment}"
        )

        return embed

    def _unlocked_commands_embed_factory(
        self,
        member: discord.Member | discord.User,
        inventory: list[utils.InventoryItem],
    ) -> utils.Embed:
        embed = utils.Embed()
        embed.colour = utils.BLUE
        embed.title = f"{utils.clean(member.display_name)}'s unlocked_commands"

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
            f"**`{progress_bar}"
            f" ({len(unlocked_commands)}/{len(unlocked_commands) + len(locked_commands)}"
            f" unlocked)`**\n\nuse {utils.format_slash_command('buy')} to unlock more items :))"
            f"\n& check out {utils.format_slash_command('help')}  to see all the other commands!"
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
                embed = self._inventory_embed_factory(member, inventory)
                interaction_id, components = self._component_factory(
                    current_page_id="INVENTORY"
                )
            elif action == "SHOW":
                if pp is None:
                    async with utils.DatabaseWrapper() as db:
                        try:
                            pp = await utils.Pp.fetch_from_user(db.conn, member.id)
                        except utils.NoPpCheckFailure:
                            if member == ctx.author:
                                raise
                            raise utils.NoPpCheckFailure(
                                f"{member.mention} ain't got a pp :("
                            )

                embed = self._show_embed_factory(member, pp)
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
        "show",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="user",
                    type=discord.ApplicationCommandOptionType.user,
                    description="Whoever's pp you want to take a peek at",
                    required=False,
                )
            ]
        ),
    )
    async def show_command(
        self, ctx: commands.SlashContext[utils.Bot], user: discord.Member | None = None
    ) -> None:
        """
        Show your pp to the whole wide world.
        """

        member = user or ctx.author

        async with utils.DatabaseWrapper() as db:
            try:
                pp = await utils.Pp.fetch_from_user(db.conn, member.id)
            except utils.NoPpCheckFailure:
                if member == ctx.author:
                    raise
                raise utils.NoPpCheckFailure(f"{member.mention} ain't got a pp :(")

        embed = self._show_embed_factory(member, pp)

        interaction_id, components = self._component_factory(current_page_id="SHOW")
        await ctx.interaction.response.send_message(embed=embed, components=components)

        await self.handle_tabs(
            ctx, member, interaction_id, components=components, pp=pp
        )

    @commands.command(
        "inventory",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="user",
                    type=discord.ApplicationCommandOptionType.user,
                    description="Whoever's pp you want to take a peek at",
                    required=False,
                )
            ]
        ),
    )
    async def inventory_command(
        self, ctx: commands.SlashContext[utils.Bot], user: discord.Member | None = None
    ) -> None:
        """
        Check out what items are in your inventory.
        """

        member = user or ctx.author

        async with utils.DatabaseWrapper() as db:
            inventory = await utils.InventoryItem.fetch(
                db.conn, {"user_id": ctx.author.id}, fetch_multiple_rows=True
            )

        embed = self._inventory_embed_factory(member, inventory)

        interaction_id, components = self._component_factory(
            current_page_id="INVENTORY"
        )
        await ctx.interaction.response.send_message(embed=embed, components=components)

        await self.handle_tabs(
            ctx, member, interaction_id, components=components, inventory=inventory
        )

    @commands.command(
        "unlocked-commands",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="user",
                    type=discord.ApplicationCommandOptionType.user,
                    description="Whoever's pp you want to take a peek at",
                    required=False,
                )
            ]
        ),
    )
    async def unlocked_commands_command(
        self, ctx: commands.SlashContext[utils.Bot], user: discord.Member | None = None
    ) -> None:
        """
        View all the commands you've unlocked.
        """

        member = user or ctx.author

        async with utils.DatabaseWrapper() as db:
            inventory = await utils.InventoryItem.fetch(
                db.conn, {"user_id": member.id}, fetch_multiple_rows=True
            )

        embed = self._unlocked_commands_embed_factory(member, inventory)

        interaction_id, components = self._component_factory(
            current_page_id="UNLOCKED_COMMANDS"
        )
        await ctx.interaction.response.send_message(embed=embed, components=components)

        await self.handle_tabs(
            ctx, member, interaction_id, components=components, inventory=inventory
        )


def setup(bot: utils.Bot):
    bot.add_cog(ShowCommandsCog(bot))
