from datetime import datetime, timedelta
import asyncio
import discord
from discord.ext import commands, vbu

from . import utils


class ShowCommandCog(vbu.Cog[utils.Bot]):
    REAL_LIFE_COMPARISONS = {
        0: "your IRL pp",
        11_800: "the Eiffel Tower",
        15_000: "the Empire State Building",
        15_157_486_080: "the distance from the earth to the moon",
    }

    def create_show_embed(
        self, pp: utils.Pp, inventory: dict[str, int], user: discord.User
    ) -> discord.Embed:
        embed = discord.Embed(
            colour=utils.BLUE,
            title=utils.limit_text(f"{pp.name.value} ({user.display_name}'s pp)", 256),
            description=f"8{'=' * min(pp.size.value // 50, 1000)}D",
        )

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
                    f"{name} - **{utils.format_int(amount)}**"
                    for name, amount in inventory.items()
                ]
            )
            or "You got no items l",
        )

        match utils.find_nearest_number(self.REAL_LIFE_COMPARISONS, pp.size.value):
            case nearest_number, -1:
                comparison_text = f"{utils.format_int(pp.size.value - nearest_number)} inches bigger than"
            case nearest_number, 0:
                comparison_text = f"the same size as"
            case nearest_number, 1:
                comparison_text = f"{utils.format_int(nearest_number - pp.size.value)} inches smaller than"

        embed.set_footer(
            text=f"Your pp is {comparison_text} {self.REAL_LIFE_COMPARISONS[nearest_number]}"
        )
        return embed

    @commands.command(application_command_meta=commands.ApplicationCommandMeta())  # type: ignore
    async def show(self, ctx: vbu.SlashContext[discord.Guild | None]) -> None:
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
                ["item_name", "item_amount"],
                fetch_multiple_rows=True,
            )

        inventory: dict[str, int] = {
            inventory_record["item_name"]: inventory_record["item_amount"]
            for inventory_record in inventory_records
        }
        
        embed = self.create_show_embed(pp, inventory, ctx.author)

        if ctx.interaction.response.is_done():
            await ctx.interaction.followup.send(embed=embed)
        else:
            await ctx.interaction.response.send_message(embed=embed)


def setup(bot: utils.Bot):
    x = ShowCommandCog(bot)
    bot.add_cog(x)
