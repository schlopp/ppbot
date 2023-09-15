import asyncio
import uuid
from datetime import datetime
from typing import Literal

import discord
from discord.ext import commands, vbu

from . import utils


class ShowCommandCog(vbu.Cog[utils.Bot]):
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

    def _component_factory(
        self, *, current_page_id: Literal["SHOW", "INVENTORY"]
    ) -> tuple[str, discord.ui.MessageComponents]:
        interaction_id = uuid.uuid4().hex
        buttons: dict[str, discord.ui.Button] = {
            "SHOW": discord.ui.Button(label="Show", custom_id=f"{interaction_id}_SHOW"),
            "INVENTORY": discord.ui.Button(
                label="Inventory", custom_id=f"{interaction_id}_INVENTORY"
            ),
        }
        buttons[current_page_id].style = discord.ButtonStyle.blurple
        buttons[current_page_id].disabled = True
        return interaction_id, discord.ui.MessageComponents(
            discord.ui.ActionRow(*buttons.values())
        )

    def _show_embed_factory(
        self, ctx: commands.SlashContext[utils.Bot], pp: utils.Pp
    ) -> utils.Embed:
        embed = utils.Embed()
        embed.colour = utils.BLUE
        embed.title = utils.limit_text(
            f"{pp.name.value} ({utils.clean(ctx.author.display_name)}'s pp)", 256
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

    async def handle_tabs(
        self,
        ctx: commands.SlashContext[utils.Bot],
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
                    self.bot, interaction_id, users=[ctx.author], timeout=60
                )
            except asyncio.TimeoutError:
                components.disable_components()
                await ctx.interaction.edit_original_message(components=components)
                break

            start = datetime.now()

            if action == "INVENTORY":
                if inventory is None:
                    async with utils.DatabaseWrapper() as db:
                        inventory = await utils.InventoryItem.fetch(
                            db.conn,
                            {"user_id": ctx.author.id},
                            fetch_multiple_rows=True,
                        )
                embed = self._inventory_embed_factory(ctx, inventory)
                interaction_id, components = self._component_factory(
                    current_page_id="INVENTORY"
                )
            elif action == "SHOW":
                if pp is None:
                    async with utils.DatabaseWrapper() as db:
                        pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id)
                embed = self._show_embed_factory(ctx, pp)
                interaction_id, components = self._component_factory(
                    current_page_id="SHOW"
                )

            print(datetime.now() - start)
            await component_interaction.response.edit_message(
                embed=embed, components=components
            )
            print(datetime.now() - start)
            print("---")

    def _inventory_embed_factory(
        self,
        ctx: commands.SlashContext[utils.Bot],
        inventory: list[utils.InventoryItem],
    ) -> utils.Embed:
        embed = utils.Embed()
        embed.colour = utils.BLUE
        embed.title = f"{utils.clean(ctx.author.display_name)}'s inventory"
        embed.description = str(inventory)
        return embed

    @commands.command(
        "show",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    async def show_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Show your pp to the whole wide world.
        """
        async with utils.DatabaseWrapper() as db:
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id)

        embed = self._show_embed_factory(ctx, pp)

        interaction_id, components = self._component_factory(current_page_id="SHOW")
        await ctx.interaction.response.send_message(embed=embed, components=components)

        await self.handle_tabs(ctx, interaction_id, components=components, pp=pp)

    @commands.command(
        "inventory",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    async def inventory_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Check out what items are in your inventory.
        """
        async with utils.DatabaseWrapper() as db:
            inventory = await utils.InventoryItem.fetch(
                db.conn, {"user_id": ctx.author.id}, fetch_multiple_rows=True
            )

        embed = self._inventory_embed_factory(ctx, inventory)

        interaction_id, components = self._component_factory(
            current_page_id="INVENTORY"
        )
        await ctx.interaction.response.send_message(embed=embed, components=components)

        await self.handle_tabs(
            ctx, interaction_id, components=components, inventory=inventory
        )


def setup(bot: utils.Bot):
    bot.add_cog(ShowCommandCog(bot))
