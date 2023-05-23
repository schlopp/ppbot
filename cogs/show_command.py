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

    @commands.command(
        "show",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    async def show_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Show your pp to the whole wide world.
        """
        async with self.bot.database() as db:
            try:
                pp = await utils.Pp.fetch(db.conn, {"user_id": ctx.author.id})
            except utils.RecordNotFoundError:
                raise commands.CheckFailure("You don't have a pp!")

            inventory_records = await utils.InventoryItem.fetch_record(
                db.conn,
                {"user_id": ctx.author.id},
                ["item_id", "item_amount"],
                fetch_multiple_rows=True,
            )

        inventory: dict[str, int] = {
            inventory_record["item_id"]: inventory_record["item_amount"]
            for inventory_record in inventory_records
        }

        embed = utils.Embed()
        embed.colour = utils.BLUE
        embed.title = utils.limit_text(
            f"{pp.name.value} ({utils.clean(ctx.author.display_name)}'s pp)", 256
        )
        embed.description = f"8{'=' * min(pp.size.value // 50, 1000)}D"

        embed.add_field(
            name="stats",
            value="- "
            + "\n- ".join(
                [
                    f"**{utils.format_int(pp.size.value)}** inches",
                    f"**{utils.format_int(pp.multiplier.value)}**x multiplier",
                ]
            ),
        )

        embed.add_field(
            name="inventory",
            value="\n".join(
                [
                    f"{utils.ItemManager.get(item_id).name} - **{utils.format_int(amount)}**"
                    for item_id, amount in inventory.items()
                ]
            )
            or "You got no items l",
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

        await ctx.interaction.response.send_message(embed=embed)


def setup(bot: utils.Bot):
    bot.add_cog(ShowCommandCog(bot))
