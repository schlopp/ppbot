import asyncio
import logging
import uuid
from datetime import timedelta
from typing import Generic, TypeVar

import discord
from discord.ext import commands, vbu, tasks

from . import utils


_T_co = TypeVar("_T_co", covariant=True)


class LeaderboardCache(utils.Object, Generic[_T_co]):
    """
    Logic in case I forget:
    You take the user's ID, put it into positions_per_user_id to
    get their position, use that minus 1 as the index for leaderboard_items
    and get the stats
    """

    __slots__ = ("positions_per_user_id", "leaderboard_items")
    positions_per_user_id: dict[int, int]
    leaderboard_items: list[tuple[utils.Pp, _T_co]]
    title: str
    label: str

    def __init__(
        self,
        *,
        logger: logging.Logger,
    ) -> None:
        self.logger = logger
        self.positions_per_user_id = {}
        self.leaderboard_items = []

    async def update(self) -> None:
        raise NotImplementedError

    def podium_value_formatter(self, position: int) -> str:
        raise NotImplementedError

    def comparison_formatter(self, position: int) -> str | None:
        raise NotImplementedError

    def generate_embed(self, ctx: commands.SlashContext[utils.Bot]) -> utils.Embed:
        embed = utils.Embed()
        embed.set_author(
            name=self.title,
            url=utils.MEME_URL,
        )

        position = self.positions_per_user_id.get(ctx.author.id)

        if position is not None:
            comparison = self.comparison_formatter(position)

            if comparison:
                embed.set_footer(
                    text=(
                        f"ur {utils.format_ordinal(position)} place on the leaderboard,"
                        f" {comparison}"
                    )
                )

            elif position == 1:
                embed.set_footer(text="you're in first place!! loser")

            else:
                embed.set_footer(
                    text=(
                        f"ur {utils.format_ordinal(position)} place on the leaderboard"
                    )
                )

        else:
            embed.set_footer(text="use /new to make your own pp :3")

        segments: list[str] = []

        for position, (pp, _) in enumerate(self.leaderboard_items, start=1):
            if position <= 3:
                prefix = ["🥇", "🥈", "🥉"][position - 1]
            elif position == 10:
                prefix = "<a:nerd:1244646167799791637>"
            else:
                prefix = "🔹"

            segments.append(
                f"{prefix} {self.podium_value_formatter(position)}"
                f" - {pp.name.value} `({pp.user_id})`"
            )

        embed.description = "\n".join(segments)

        return embed


class SizeLeaderboardCache(LeaderboardCache[int]):
    title = "the biggest pps in the entire universe"
    label = "Size"

    async def update(self) -> None:
        self.logger.debug("Updating size leaderboard cache...")

        new_position_per_user_id: dict[int, int] = {}
        new_leaderboard_items: list[tuple[utils.Pp, int]] = []

        async with utils.DatabaseWrapper() as db:
            records = await db(
                """
                SELECT *
                FROM pps
                ORDER BY pp_size DESC
                """
            )
            for n, record in enumerate(records):
                if n < 10:
                    pp_data = dict(record)
                    pp = utils.Pp.from_record(pp_data)
                    new_leaderboard_items.append((pp, pp.size.value))
                new_position_per_user_id[record["user_id"]] = n + 1

        self.positions_per_user_id = new_position_per_user_id
        self.leaderboard_items = new_leaderboard_items

        self.logger.debug("Size leaderboard cache updated")

    def podium_value_formatter(self, position: int) -> str:
        size = self.leaderboard_items[position - 1][1]
        return utils.format_inches(size)

    def comparison_formatter(self, position: int) -> str | None:
        better_pp_size: int | None = None

        if position == 1:
            return

        pp_size = self.leaderboard_items[position - 1][1]
        better_pp_size = self.leaderboard_items[position - 2][1]

        difference = better_pp_size - pp_size

        return (
            f"{utils.format_inches(difference, markdown=None)} behind"
            f" {utils.format_ordinal(position - 1)} place"
        )


class MultiplierLeaderboardCache(LeaderboardCache[int]):
    title = "the craziest multipliers across all of pp bot (boosts not included)"
    label = "Multiplier"

    async def update(self) -> None:
        self.logger.debug("Updating multiplier leaderboard cache...")

        new_position_per_user_id: dict[int, int] = {}
        new_leaderboard_items: list[tuple[utils.Pp, int]] = []

        async with utils.DatabaseWrapper() as db:
            records = await db(
                """
                SELECT *
                FROM pps
                ORDER BY pp_multiplier DESC
                """
            )
            for n, record in enumerate(records):
                if n < 10:
                    pp_data = dict(record)
                    pp = utils.Pp.from_record(pp_data)
                    new_leaderboard_items.append((pp, pp.multiplier.value))
                new_position_per_user_id[record["user_id"]] = n + 1

        self.positions_per_user_id = new_position_per_user_id
        self.leaderboard_items = new_leaderboard_items

        self.logger.debug("Multiplier leaderboard cache updated")

    def podium_value_formatter(self, position: int) -> str:
        multiplier = self.leaderboard_items[position - 1][1]
        return f"**{utils.format_int(multiplier)}x** multiplier"

    def comparison_formatter(self, position: int) -> str | None:
        better_multiplier: int | None = None

        if position == 1:
            return

        multiplier = self.leaderboard_items[position - 1][1]
        better_multiplier = self.leaderboard_items[position - 2][1]

        difference = better_multiplier - multiplier

        return (
            f"{utils.format_int(difference)} multipliers behind"
            f" {utils.format_ordinal(position - 1)} place"
        )


class DonationLeaderboardCache(LeaderboardCache[int]):
    title = "the most generous people sharing their pp with everyone"
    label = "Donations"

    async def update(self) -> None:
        self.logger.debug("Updating donation leaderboard cache...")

        new_position_per_user_id: dict[int, int] = {}
        new_leaderboard_items: list[tuple[utils.Pp, int]] = []

        async with utils.DatabaseWrapper() as db:
            records = await db(
                """
                WITH donation_totals AS (
                    SELECT
                        donor_id,
                        SUM(amount) AS total_donations
                    FROM donations
                    GROUP BY donor_id
                )
                SELECT
                    pps.*,
                    donation_totals.total_donations
                FROM donation_totals
                JOIN pps
                    ON donation_totals.donor_id = pps.user_id
                ORDER BY donation_totals.total_donations DESC
                """
            )
            for n, record in enumerate(records):
                if n < 10:
                    pp_data = dict(record)
                    total_donations = pp_data.pop("total_donations")
                    pp = utils.Pp.from_record(pp_data)
                    new_leaderboard_items.append((pp, total_donations))
                new_position_per_user_id[record["user_id"]] = n + 1

        self.positions_per_user_id = new_position_per_user_id
        self.leaderboard_items = new_leaderboard_items

        self.logger.debug("Donation leaderboard cache updated")

    def podium_value_formatter(self, position: int) -> str:
        amount = self.leaderboard_items[position - 1][1]
        return f"{utils.format_inches(amount)} donated"

    def comparison_formatter(self, position: int) -> str | None:
        better_multiplier: int | None = None

        if position == 1:
            return

        multiplier = self.leaderboard_items[position - 1][1]
        better_multiplier = self.leaderboard_items[position - 2][1]

        difference = better_multiplier - multiplier

        return (
            f"{utils.format_int(difference)} multipliers behind"
            f" {utils.format_ordinal(position - 1)} place"
        )


class LeaderboardCommandCog(vbu.Cog[utils.Bot]):
    LEADERBOARD_CACHE_REFRESH_TIME = timedelta(seconds=15)
    size_leaderboard_cache = SizeLeaderboardCache(
        logger=logging.getLogger(
            "vbu.bot.cog.LeaderboardCommandCog.SizeLeaderboardCache"
        )
    )
    multiplier_leaderboard_cache = MultiplierLeaderboardCache(
        logger=logging.getLogger(
            "vbu.bot.cog.LeaderboardCommandCog.MultiplierLeaderboardCache"
        )
    )
    donation_leaderboard_cache = DonationLeaderboardCache(
        logger=logging.getLogger(
            "vbu.bot.cog.LeaderboardCommandCog.DonationLeaderboardCache"
        )
    )
    CATEGORIES: dict[str, LeaderboardCache] = {
        "SIZE": size_leaderboard_cache,
        "MULTIPLIER": multiplier_leaderboard_cache,
        "DONATION": donation_leaderboard_cache,
    }

    def __init__(self, bot: utils.Bot, logger_name: str | None = None):
        super().__init__(bot, logger_name)
        self.cache_leaderboard.start()

    async def cog_unload(self) -> None:
        self.cache_leaderboard.cancel()

    @tasks.loop(seconds=int(LEADERBOARD_CACHE_REFRESH_TIME.total_seconds()))
    async def cache_leaderboard(self) -> None:
        self.logger.debug("Updating leaderboard caches...")
        await self.size_leaderboard_cache.update()
        await self.multiplier_leaderboard_cache.update()
        await self.donation_leaderboard_cache.update()

    @commands.command(
        "leaderboard",
        utils.Command,
        category=utils.CommandCategory.STATS,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.is_slash_command()
    async def leaderboard_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Check out the biggest pps in the world
        """

        embed = self.size_leaderboard_cache.generate_embed(ctx)

        interaction_id = uuid.uuid4().hex
        select_menu = discord.ui.SelectMenu(
            custom_id=f"{interaction_id}_CATEGORY",
            options=[
                discord.ui.SelectOption(
                    label=leaderboard_cache.label,
                    value=category,
                    default=category == "SIZE",
                )
                for category, leaderboard_cache in self.CATEGORIES.items()
            ],
        )
        components = discord.ui.MessageComponents(discord.ui.ActionRow(select_menu))

        await ctx.interaction.response.send_message(
            embed=embed,
            components=components,
        )

        while True:
            try:
                interaction, _ = await utils.wait_for_component_interaction(
                    self.bot, interaction_id, users=[ctx.author], actions=["CATEGORY"]
                )
            except asyncio.TimeoutError:
                components.disable_components()
                await ctx.interaction.edit_original_message(components=components)
                break

            category = interaction.values[0]
            leaderboard_cache = self.CATEGORIES[category]

            embed = leaderboard_cache.generate_embed(ctx)

            for option in select_menu.options:
                if option.value == category:
                    option.default = True
                else:
                    option.default = False

            await interaction.response.edit_message(embed=embed, components=components)


async def setup(bot: utils.Bot):
    await bot.add_cog(LeaderboardCommandCog(bot))
