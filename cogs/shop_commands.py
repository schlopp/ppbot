import math
import uuid
from collections import Counter
from difflib import SequenceMatcher
from collections.abc import Awaitable, Callable
from typing import Self, Literal, Iterable

import discord
from discord.ext import commands, vbu

from . import utils


ShopPaginatorActions = utils.PaginatorActions | Literal["SELECT_CATEGORY"]


class ShopPaginator(utils.Paginator[utils.Item, ShopPaginatorActions]):
    def __init__(
        self,
        bot: utils.Bot,
        items: Iterable[utils.Item],
        *,
        loader: Callable[[Self, tuple[utils.Item]], Awaitable[utils.Embed]],
        per_page: int = 5,
    ) -> None:
        self.categories: set[str] = {
            utils.MultiplierItem.category,
            utils.BuffItem.category,
            utils.ToolItem.category,
            utils.UselessItem.category,
        }
        super().__init__(bot, items, loader=loader, per_page=per_page)
        self._paginator_category_select_menu = discord.ui.SelectMenu(
            custom_id=f"{self.id}_SELECT_CATEGORY",
            options=[
                discord.ui.SelectOption(
                    label="Multipliers",
                    value=utils.MultiplierItem.category,
                    default=True,
                ),
                discord.ui.SelectOption(
                    label="Buffs", value=utils.BuffItem.category, default=True
                ),
                discord.ui.SelectOption(
                    label="Tools",
                    value=utils.ToolItem.category,
                    default=True,
                ),
                discord.ui.SelectOption(
                    label="Useless Items",
                    value=utils.UselessItem.category,
                    default=True,
                ),
            ],
            placeholder="Categories",
            max_values=4,
        )

        self._components.components.insert(
            0, discord.ui.ActionRow(self._paginator_category_select_menu)
        )

    def _update_components(self, *, disable_all: bool = False) -> None:
        super()._update_components(disable_all=disable_all)
        if disable_all:
            return

        for category_option in self._paginator_category_select_menu.options:
            if category_option.value in self.categories:
                category_option.default = True
                continue
            category_option.default = False

    def handle_interaction(
        self, interaction: discord.ComponentInteraction, action: ShopPaginatorActions
    ) -> None:
        if action == "SELECT_CATEGORY":
            categories = interaction.data.get("values")
            assert categories is not None
            self.categories = set(categories)
            self.max_pages = math.ceil(len(self.items) / self.per_page)
            self.current_page = min(self.current_page, self.max_pages - 1)
        return super().handle_interaction(interaction, action)

    @property
    def items(self) -> tuple[utils.Item]:
        return tuple(item for item in self._items if item.category in self.categories)


class ShopCommandCog(vbu.Cog[utils.Bot]):
    @commands.command(
        "shop",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def shop_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Check out what tools, multipliers, buffs, and other items are for sale!
        """

        async with self.bot.database() as db:
            try:
                pp = await utils.Pp.fetch(
                    db.conn,
                    {"user_id": ctx.author.id},
                )
            except utils.RecordNotFoundError:
                raise commands.CheckFailure("You don't have a pp!")

            inventory = {
                inventory_item.id: inventory_item
                for inventory_item in await utils.InventoryItem.fetch(
                    db.conn,
                    required_values={"user_id": ctx.author.id},
                    fetch_multiple_rows=True,
                )
            }

        # assert isinstance(ctx.channel, discord.TextChannel)
        # await ctx.channel.send(repr(utils.ItemManager.items))
        embed = utils.Embed(include_tip=False)
        embed.color = utils.BLUE

        async def paginator_loader(
            paginator: ShopPaginator, items: tuple[utils.Item]
        ) -> utils.Embed:
            embed.title = f"SHOP ({pp.format_growth(pp.size.value)})"
            if paginator.categories != {
                utils.MultiplierItem.category,
                utils.BuffItem.category,
                utils.ToolItem.category,
                utils.UselessItem.category,
            }:
                embed.title += (
                    f" - {len(paginator.categories)}"
                    f" categor{'y' if len(paginator.categories) == 1 else 'ies'} selected"
                )

            listings: list[str] = []

            for item in items:
                listing_title = (
                    f"[**`{item.category}`**]({utils.MEME_URL}) **{item.name}**"
                )

                try:
                    listing_title += f" ({inventory[item.id].amount.value})"
                except KeyError:
                    pass

                listing_title += f" — {pp.format_growth(item.price, markdown=None)}"

                if item.price > pp.size.value:
                    listing_title += " (too expensive!)"

                listing_description = f"{item.description}"

                listing_details: list[str] = []

                if isinstance(item, utils.MultiplierItem):
                    listing_details.append(
                        f"Gives you a permanent **+{utils.format_int(item.gain)} multiplier**"
                    )
                elif isinstance(item, utils.BuffItem):
                    listing_details.extend(item.specified_details)

                    if item.multiplier is not None:
                        listing_details.append(
                            f"Increases your multiplier by"
                            f" **{utils.format_int(round(item.multiplier * 100), utils.IntFormatType.ABBREVIATED_UNIT)}%**"
                        )

                    cooldown_message = (
                        f"Lasts **{utils.format_time(item.duration.total_seconds())}**"
                    )

                    if item.cooldown is not None:
                        listing_details.append(
                            cooldown_message
                            + f" with a **{utils.format_time(item.cooldown.total_seconds())}** cooldown"
                        )
                    else:
                        listing_details.append(cooldown_message)
                        listing_details.append(
                            f"**Stackable:** You can take multiple at once to increase duration"
                        )
                elif isinstance(item, utils.ToolItem):
                    listing_details.append(
                        f"Unlocks the **/{item.associated_command_name}** command"
                    )

                if listing_details:
                    listing_description += "\n• " + "\n• ".join(listing_details)

                listings.append(f"{listing_title}\n{listing_description}")

            embed.description = "\n\n".join(listings)
            embed.set_footer(
                text=f"page {paginator.current_page + 1}/{paginator.max_pages} • use /buy to buy items"
            )

            return embed

        paginator = ShopPaginator(
            self.bot, utils.ItemManager.items.values(), loader=paginator_loader
        )
        await paginator.start(ctx.interaction)

    @commands.command(
        "buy",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="item",
                    type=discord.ApplicationCommandOptionType.string,
                    description="The item u wanna buy",
                    autocomplete=True,
                ),
                discord.ApplicationCommandOption(
                    name="amount",
                    type=discord.ApplicationCommandOptionType.integer,
                    description="How many of this item u wanna buy",
                ),
            ]
        ),
    )
    @commands.is_slash_command()
    async def buy_command(
        self, ctx: commands.SlashContext[utils.Bot], item: str, amount: int
    ) -> None:
        async with self.bot.database() as db, db.transaction():
            try:
                pp = await utils.Pp.fetch(
                    db.conn,
                    {"user_id": ctx.author.id},
                    lock=utils.RowLevelLockMode.FOR_UPDATE,
                )
            except utils.RecordNotFoundError:
                raise commands.CheckFailure("You don't have a pp!")

            interaction_id = uuid.uuid4().hex

            if (
                item not in utils.ItemManager.items
                and item not in utils.ItemManager.items_by_name
            ):
                embed = utils.Embed(include_tip=False)
                embed.colour = utils.RED
                embed.title = "Purchase failed: Unknown item"
                embed.description = (
                    f"The item {item!r} doesn't exist!"
                    " Make sure you select one of the options or spell the item's name correctly."
                )

                buttons = []

                item_value = item.lower()
                similar_items = Counter(
                    {
                        item: max(
                            round(
                                SequenceMatcher(
                                    None, item_value, item.name.lower()
                                ).ratio()
                                * 1000
                            ),
                            round(
                                SequenceMatcher(
                                    None, item_value, item.id.lower()
                                ).ratio()
                                * 1000
                            ),
                            500
                            if item_value in item.name.lower()
                            else 500
                            if item_value in item.id.lower()
                            else 0,
                        )
                        for item in utils.ItemManager.items.values()
                    }
                ).most_common(3)

                if similar_items[0][1] >= 500:
                    buttons.append(
                        discord.ui.Button(
                            label="Did you mean:",
                            disabled=True,
                        )
                    )

                    for item_object, match_amount in similar_items:
                        if match_amount < 500:
                            continue

                        buttons.append(
                            discord.ui.Button(
                                # label=f"{item_object.name} ({match_amount / 10:.1f}% match)",
                                label=item_object.name,
                                custom_id=f"{interaction_id}_{item_object.id}",
                                style=discord.ui.ButtonStyle.green,
                            )
                        )

                    buttons.append(
                        discord.ui.Button(
                            label="Cancel",
                            custom_id=f"{interaction_id}_CANCEL",
                            style=discord.ui.ButtonStyle.red,
                        )
                    )

                if not buttons:
                    await ctx.interaction.response.send_message(embed=embed)
                    return

                components = discord.ui.MessageComponents(
                    discord.ui.ActionRow(*buttons)
                )
                await ctx.interaction.response.send_message(
                    embed=embed,
                    components=components,
                )
                component_interaction = await self.bot.wait_for(
                    "component_interaction",
                    check=lambda i: i.user == ctx.author and i.custom_id.startswith(interaction_id),
                    timeout=60,
                )
                _, action = component_interaction.custom_id.split("_", 1)

                if action == "CANCEL":
                    await ctx.interaction.delete_original_message()
                    return

                item_object = utils.ItemManager.get(action)

                async def responder(**kwargs) -> None:
                    await component_interaction.response.edit_message(**kwargs)

            else:
                item_object = utils.ItemManager.get(item)

                async def responder(**kwargs) -> None:
                    kwargs = {k: v for k, v in kwargs.items() if v is not None}
                    await ctx.interaction.response.send_message(**kwargs)

            if isinstance(item_object, utils.MultiplierItem):
                price, gain = item_object.get_scaled_values(
                    amount, multiplier=pp.multiplier.value
                )
            else:
                price = item_object.price * amount
                gain = None

            embed = utils.Embed(include_tip=True)
            embed.colour = utils.BLUE
            embed.title = f"Buying {item_object.format_amount(amount, markdown=None)}"
            embed.description = (
                f"Are you sure that you want to buy {item_object.format_amount(amount)}"
                f" for {pp.format_growth(price)}?"
            )

            await responder(
                content=(
                    f"{amount!r} {pp.format_growth(price)} {item_object!r} :: gain {gain!r}"
                ),
                embed=embed,
                components=discord.ui.MessageComponents(
                    discord.ui.ActionRow(
                        discord.ui.Button(
                            label="Yes",
                            custom_id=f"{interaction_id}_YES",
                            style=discord.ButtonStyle.green,
                        ),
                        discord.ui.Button(
                            label="No",
                            custom_id=f"{interaction_id}_NO",
                            style=discord.ButtonStyle.red,
                        ),
                    )
                ),
            )

    @buy_command.autocomplete  # type: ignore
    async def buy_command_autocomplete(
        self, _: commands.SlashContext[utils.Bot], interaction: discord.Interaction
    ) -> None:
        assert interaction.options
        item_value = (interaction.options[0].value or "").lower()

        await interaction.response.send_autocomplete(
            [
                discord.ApplicationCommandOptionChoice(
                    name=f"{item.name} ({utils.format_int(item.price)} inches)"
                    if not isinstance(item, utils.MultiplierItem)
                    else item.name,
                    value=item.id,
                )
                for item in utils.ItemManager.items.values()
                if not item_value
                or item_value in item.name.lower()
                or item_value in item.id.lower()
                or SequenceMatcher(None, item_value, item.name.lower()).quick_ratio()
                > 0.7
                or SequenceMatcher(None, item_value, item.id.lower()).quick_ratio()
                > 0.7
            ]
        )


def setup(bot: utils.Bot):
    bot.add_cog(ShopCommandCog(bot))
