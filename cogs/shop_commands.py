import asyncio
import uuid
from collections import Counter
from difflib import SequenceMatcher
from typing import Literal

import discord
from discord.ext import commands, vbu

from . import utils


ShopPaginatorActions = utils.PaginatorActions | Literal["SELECT_CATEGORY"]


class ShopCommandCog(vbu.Cog[utils.Bot]):
    MAX_MULTIPLIER_PURCHASE_AMOUNT = 10**6

    def format_listing(
        self, item: utils.Item, *, pp: utils.Pp, amount_owned: int | None = None
    ) -> str:
        listing_title = f"[**`{item.category}`**]({utils.MEME_URL}) **{item.name}**"

        if amount_owned is not None:
            listing_title += f" ({amount_owned})"

        if isinstance(item, utils.MultiplierItem):
            price, _ = item.compute_cost(1, current_multiplier=pp.multiplier.value)
        else:
            price = item.price

        listing_title += f" — {pp.format_growth(price, markdown=None)}"

        if item.price > pp.size.value:
            listing_title += " (too expensive!)"

        listing_description = f"{item.description}"
        listing_details: list[str] = []

        if isinstance(item, utils.MultiplierItem):
            listing_details.append(
                f"Gives you a permanent **+{utils.format_int(item.gain)}** multiplier"
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
                    + f" with **{utils.format_time(item.cooldown.total_seconds(), adjective=True)}** cooldown"
                )
            else:
                listing_details.append(cooldown_message)
                listing_details.append(
                    f"**Stackable:** You can take multiple at once to increase duration"
                )
        elif isinstance(item, utils.ToolItem):
            listing_details.append(
                f"Unlocks the {item.associated_command_link} command"
            )

        if listing_details:
            listing_description += "\n" + utils.format_iterable(listing_details)

        return f"{listing_title}\n{listing_description}"

    @commands.command(
        "shop",
        utils.Command,
        category=utils.CommandCategory.SHOP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def shop_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Check out what tools, multipliers, buffs, and other items are for sale!
        """

        async with utils.DatabaseWrapper() as db:
            pp = await utils.Pp.fetch_from_user(
                db.conn,
                ctx.author.id,
            )

            inventory = {
                inventory_item.id: inventory_item
                for inventory_item in await utils.InventoryItem.fetch(
                    db.conn,
                    required_values={"user_id": ctx.author.id},
                    fetch_multiple_rows=True,
                )
            }

        embed = utils.Embed()
        embed.color = utils.BLUE

        async def paginator_loader(
            paginator: utils.CategorisedPaginator, items: tuple[utils.Item, ...]
        ) -> utils.Embed:
            embed.title = f"SHOP ({pp.format_growth(pp.size.value)})"
            if "ALL" not in paginator.active_categories:
                embed.title += (
                    f" - {len(paginator.active_categories)}"
                    f" categor{'y' if len(paginator.active_categories) == 1 else 'ies'} selected"
                )

            listings: list[str] = []

            for item in items:
                try:
                    amount_owned = inventory[item.id].amount.value
                except KeyError:
                    amount_owned = None

                listings.append(
                    self.format_listing(item, pp=pp, amount_owned=amount_owned)
                )

            embed.description = "\n\n".join(listings)
            embed.set_footer(
                text=f"page {paginator.current_page + 1}/{paginator.max_pages} • use /buy to buy items"
            )

            return embed

        paginator = utils.CategorisedPaginator(
            self.bot,
            [
                item
                for item in utils.ItemManager.items.values()
                if not isinstance(item, utils.BuffItem)
            ],
            categories={
                ItemClass.category: ItemClass.category_name
                for ItemClass in [
                    utils.MultiplierItem,
                    utils.ToolItem,
                    utils.UselessItem,
                ]
            },
            loader=paginator_loader,
            categoriser=lambda item, active_categories: item.category
            in active_categories,
        )
        await paginator.start(ctx.interaction)

    @commands.command(
        "buy",
        utils.Command,
        category=utils.CommandCategory.SHOP,
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
                    type=discord.ApplicationCommandOptionType.string,
                    description="How many of this item u wanna buy",
                ),
            ]
        ),
    )
    @commands.is_slash_command()
    async def buy_command(
        self, ctx: commands.SlashContext[utils.Bot], item: str, amount: str
    ) -> None:
        if amount not in {"all", "max"} and not (
            amount.isnumeric() and int(amount) >= 1
        ):
            raise utils.InvalidArgumentAmount(
                argument="amount", min=0, special_amounts=["all", "max"]
            )

        async with (
            utils.DatabaseWrapper() as db,
            db.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, "You're still busy buying an item!"
            ),
        ):
            try:
                pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)
            except utils.RecordNotFoundError:
                raise utils.PpMissing("You don't have a pp!")

            interaction_id = uuid.uuid4().hex

            if (
                item not in utils.ItemManager.items
                and item not in utils.ItemManager.items_by_name
            ):
                embed = utils.Embed()
                embed.colour = utils.RED
                embed.title = "Purchase failed: Unknown item"
                embed.description = (
                    f"The item {utils.clean(item)!r} doesn't exist!"
                    " Make sure you select one of the options or spell the item's name correctly"
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
                            (
                                500
                                if item_value in item.name.lower()
                                else 500 if item_value in item.id.lower() else 0
                            ),
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

                try:
                    component_interaction = await self.bot.wait_for(
                        "component_interaction",
                        check=lambda i: i.user == ctx.author
                        and i.custom_id.startswith(interaction_id),
                        timeout=180,
                    )
                except asyncio.TimeoutError:
                    try:
                        await ctx.interaction.edit_original_message(
                            embed=utils.Embed.as_timeout("Purchase failed"),
                            components=components.disable_components(),
                        )
                    except:
                        pass
                    return

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

            embed = utils.Embed()

            if amount in {"all", "max"}:
                if isinstance(item_object, utils.MultiplierItem):
                    amount_number, cost, gain = item_object.compute_max_purchase(
                        available_inches=pp.size.value,
                        current_multiplier=pp.multiplier.value,
                    )
                    if amount_number < 1:
                        embed.colour = utils.RED
                        embed.title = f"Purchase failed - ur broke"

                        cost, _ = item_object.compute_cost(
                            1, current_multiplier=pp.multiplier.value
                        )
                        embed.description = (
                            "You literally can't even afford {item} lmao."
                            " Come back when you have **{inches_more_required}** more inches loser"
                        ).format(
                            item=item_object.format_amount(
                                1, article=item_object.indefinite_article
                            ),
                            inches_more_required=utils.format_int(cost - pp.size.value),
                        )
                        embed.add_tip()

                        await responder(embed=embed, components=None, content=None)
                        return
                else:
                    amount_number = pp.size.value // item_object.price
                    cost = amount_number * item_object.price
                    gain = None
            else:
                amount_number = int(amount)
                if isinstance(item_object, utils.MultiplierItem):
                    if amount_number > self.MAX_MULTIPLIER_PURCHASE_AMOUNT:
                        embed.colour = utils.RED
                        embed.title = (
                            f"Purchase failed - buying too many multipliers at once"
                        )
                        embed.description = (
                            f"You can't buy more than"
                            f" {utils.format_int(self.MAX_MULTIPLIER_PURCHASE_AMOUNT)} multipliers"
                            f" at once, sorry!"
                        )
                        embed.add_tip()

                        await responder(embed=embed, components=None, content=None)
                        return
                    cost, gain = item_object.compute_cost(
                        amount_number, current_multiplier=pp.multiplier.value
                    )
                else:
                    cost = amount_number * item_object.price
                    gain = None

            item_formatted = item_object.format_amount(
                amount_number, article=item_object.indefinite_article
            )

            if cost > pp.size.value:
                embed.colour = utils.RED
                embed.title = f"Purchase failed - ur broke"
                embed.description = (
                    "You need {inches_more_required} more to afford {item}"
                    " <:sadge:1194351982044008561>"
                ).format(
                    inches_more_required=utils.format_int(cost - pp.size.value),
                    item=item_formatted,
                )
                embed.add_tip()

                await responder(embed=embed, components=None, content=None)
                return

            embed.colour = utils.BLUE
            embed.title = (
                f"Buying {item_object.format_amount(amount_number, markdown=None)}"
            )
            embed.description = (
                f"Are you sure that you want to buy {item_formatted}"
                f" for {pp.format_growth(cost)}? You'll have"
                f" {pp.format_growth(pp.size.value - cost)} left"
                f"\n\n{self.format_listing(item_object, pp=pp)}"
            )

            components = discord.ui.MessageComponents(
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
            )

            await responder(
                embed=embed,
                components=components,
            )

            try:
                component_interaction = await self.bot.wait_for(
                    "component_interaction",
                    check=lambda i: i.user == ctx.author
                    and i.custom_id.startswith(interaction_id),
                    timeout=180,
                )
            except asyncio.TimeoutError:
                try:
                    await ctx.interaction.edit_original_message(
                        embed=utils.Embed.as_timeout("Purchase failed"),
                        components=components.disable_components(),
                    )
                except discord.HTTPException:
                    pass
                return

            _, action = component_interaction.custom_id.split("_", 1)

            if action == "NO":
                embed.colour = utils.RED
                embed.title = "Purchase cancelled"
                embed.description = (
                    f"You've cancelled your purchase of {item_formatted}"
                    f" for {pp.format_growth(cost)}"
                )
                await component_interaction.response.edit_message(
                    embed=embed, components=None
                )
                return

            pp.size.value -= cost
            embed.colour = utils.GREEN
            embed.title = "Purchase successful"

            if gain is not None:
                pp.multiplier.value += gain
                embed.description = (
                    "*You take"
                    f" {item_formatted}"
                    f" for {pp.format_growth(cost)} and feel a sudden surge of power coursing"
                    f" through your pp's veins. You gain an additional"
                    f" **+{utils.format_int(gain)}** multiplier.*"
                    f"\n\nYou now have {pp.format_growth(pp.size.value)} and a"
                    f" **{utils.format_int(pp.multiplier.value)}x** multiplier!"
                )
            else:
                try:
                    inventory_item = await utils.InventoryItem.fetch(
                        db.conn,
                        {"user_id": ctx.author.id, "id": item_object.id},
                        lock=utils.RowLevelLockMode.FOR_UPDATE,
                    )
                except utils.RecordNotFoundError:
                    inventory_item = utils.InventoryItem(
                        ctx.author.id, item_object.id, 0
                    )

                inventory_item.amount.value += amount_number
                await inventory_item.update(db.conn)

                embed.description = (
                    f"You've successfully purchased {item_formatted}"
                    f" for {pp.format_growth(cost)}. You now have"
                    f" {pp.format_growth(pp.size.value)} and"
                    f" {inventory_item.format_item(article=utils.Article.INDEFINITE)}!"
                )

            await pp.update(db.conn)
            await component_interaction.response.edit_message(
                embed=embed, components=None
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
                    name=(
                        f"{item.name} ({utils.format_int(item.price)} inches)"
                        if not isinstance(item, utils.MultiplierItem)
                        else item.name
                    ),
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


async def setup(bot: utils.Bot):
    await bot.add_cog(ShopCommandCog(bot))
