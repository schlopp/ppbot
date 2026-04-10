import asyncio
import logging
import uuid
from datetime import timedelta
from typing import Generic, TypeVar, Literal, cast, Self

import discord
from discord.ext import commands, vbu, tasks

from . import utils

_T_co = TypeVar("_T_co", covariant=True)
_V_co = TypeVar("_V_co", covariant=True)


LeaderboardScope = Literal["GLOBAL", "GUILD"]


class LeaderboardCache(utils.Object, Generic[_T_co, _V_co]):
    """
    Logic in case I forget:
    You take the user's ID, put it into positions_per_user_id to
    get their position, use that minus 1 as the index for leaderboard_items
    and get the stats
    """

    __slots__ = ("positions_per_user_id", "leaderboard_items")
    positions_per_user_id: dict[int, int]
    leaderboard_items: list[tuple[utils.Pp, _T_co]]
    values_by_position: list[_V_co]
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
        self.values_by_position = []

    @classmethod
    def for_guild(cls: type[Self], guild: discord.Guild) -> Self:
        raise NotImplementedError

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

        user_position = self.positions_per_user_id.get(ctx.author.id)

        if user_position is not None:
            comparison = self.comparison_formatter(user_position)

            if comparison:
                embed.set_footer(
                    text=(
                        f"ur {utils.format_ordinal(user_position)} place on the leaderboard,"
                        f" {comparison}"
                    )
                )

            elif user_position == 1:
                embed.set_footer(text="you're in first place!! loser")

            else:
                embed.set_footer(
                    text=(
                        f"ur {utils.format_ordinal(user_position)} place on the leaderboard"
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

            if position == user_position:
                prefix += "🫵"

            segments.append(
                f"{prefix} {self.podium_value_formatter(position)}"
                f" - {pp.name.value} `({pp.user_id})`"
            )

        embed.description = "\n".join(segments)

        return embed


class SizeLeaderboardCache(LeaderboardCache[int, int]):
    """Values by position: list[overtake_difference: int]"""

    title = "the biggest pps in the entire universe"
    label = "Size"

    @classmethod
    def for_guild(cls: type[Self], guild: discord.Guild) -> Self:
        leaderboard_cache = cls(
            logger=logging.getLogger(
                "vbu.bot.cog.LeaderboardCommandCog.SizeLeaderboardCache"
                f"-GUILD-{guild.id}"
            ),
        )

        leaderboard_cache.title = "the biggest pps in this server"

        async def guild_update():
            leaderboard_cache.logger.debug("Updating size leaderboard cache...")

            new_position_per_user_id: dict[int, int] = {}
            new_leaderboard_items: list[tuple[utils.Pp, int]] = []
            new_values_by_position: list[int] = []

            async with utils.DatabaseWrapper() as db:
                records = await db(
                    """
                    SELECT pps.*
                    FROM pps
                    INNER JOIN pp_guilds ON
                        pp_guilds.user_id=pps.user_id
                        AND pp_guilds.guild_id=$1 
                    ORDER BY pp_size DESC
                    """,
                    guild.id,
                )
                next_place: utils.Pp | None = None
                for n, record in enumerate(records):
                    pp_data = dict(record)
                    pp = utils.Pp.from_record(pp_data)

                    if n < 10:
                        new_leaderboard_items.append((pp, pp.size.value))

                    if next_place is None:
                        overtake_difference = 0
                    else:
                        overtake_difference = next_place.size.value - pp.size.value

                    new_position_per_user_id[record["user_id"]] = n + 1
                    new_values_by_position.append(overtake_difference)
                    next_place = pp

            leaderboard_cache.positions_per_user_id = new_position_per_user_id
            leaderboard_cache.leaderboard_items = new_leaderboard_items
            leaderboard_cache.values_by_position = new_values_by_position

            leaderboard_cache.logger.debug("Size leaderboard cache updated")

        leaderboard_cache.update = guild_update

        return leaderboard_cache

    async def update(self) -> None:
        self.logger.debug("Updating size leaderboard cache...")

        new_position_per_user_id: dict[int, int] = {}
        new_leaderboard_items: list[tuple[utils.Pp, int]] = []
        new_values_by_position: list[int] = []

        async with utils.DatabaseWrapper() as db:
            records = await db("""
                SELECT *
                FROM pps
                ORDER BY pp_size DESC
                """)
            next_place: utils.Pp | None = None
            for n, record in enumerate(records):
                pp_data = dict(record)
                pp = utils.Pp.from_record(pp_data)

                if n < 10:
                    new_leaderboard_items.append((pp, pp.size.value))

                if next_place is None:
                    overtake_difference = 0
                else:
                    overtake_difference = next_place.size.value - pp.size.value

                new_position_per_user_id[record["user_id"]] = n + 1
                new_values_by_position.append(overtake_difference)
                next_place = pp

        self.positions_per_user_id = new_position_per_user_id
        self.leaderboard_items = new_leaderboard_items
        self.values_by_position = new_values_by_position

        self.logger.debug("Size leaderboard cache updated")

    def podium_value_formatter(self, position: int) -> str:
        size = self.leaderboard_items[position - 1][1]
        return utils.format_inches(size)

    def comparison_formatter(self, position: int) -> str | None:
        if position == 1:
            return

        difference = self.values_by_position[position - 1]

        return (
            f"{utils.format_inches(difference, markdown=None)} behind"
            f" {utils.format_ordinal(position - 1)} place"
        )


class MultiplierLeaderboardCache(LeaderboardCache[int, int]):
    title = "the craziest multipliers across all of pp bot (boosts not included)"
    label = "Multiplier"

    @classmethod
    def for_guild(cls: type[Self], guild: discord.Guild) -> Self:
        leaderboard_cache = cls(
            logger=logging.getLogger(
                "vbu.bot.cog.LeaderboardCommandCog.MultiplierLeaderboardCache"
                f"-GUILD-{guild.id}"
            ),
        )

        leaderboard_cache.title = (
            "the craziest multipliers in this server (boosts not included)"
        )

        async def guild_update():
            leaderboard_cache.logger.debug("Updating multiplier leaderboard cache...")

            new_position_per_user_id: dict[int, int] = {}
            new_leaderboard_items: list[tuple[utils.Pp, int]] = []
            new_values_by_position: list[int] = []

            async with utils.DatabaseWrapper() as db:
                records = await db(
                    """
                    SELECT pps.*
                    FROM pps
                    INNER JOIN pp_guilds ON
                        pp_guilds.user_id=pps.user_id
                        AND pp_guilds.guild_id=$1
                    ORDER BY pp_multiplier DESC
                    """,
                    guild.id,
                )
                next_place: utils.Pp | None = None
                for n, record in enumerate(records):
                    pp_data = dict(record)
                    pp = utils.Pp.from_record(pp_data)

                    if n < 10:
                        new_leaderboard_items.append((pp, pp.multiplier.value))

                    if next_place is None:
                        overtake_difference = 0
                    else:
                        overtake_difference = (
                            next_place.multiplier.value - pp.multiplier.value
                        )

                    new_position_per_user_id[record["user_id"]] = n + 1
                    new_values_by_position.append(overtake_difference)
                    next_place = pp

            leaderboard_cache.positions_per_user_id = new_position_per_user_id
            leaderboard_cache.leaderboard_items = new_leaderboard_items
            leaderboard_cache.values_by_position = new_values_by_position

            leaderboard_cache.logger.debug("Multiplier leaderboard cache updated")

        leaderboard_cache.update = guild_update

        return leaderboard_cache

    async def update(self) -> None:
        self.logger.debug("Updating multiplier leaderboard cache...")

        new_position_per_user_id: dict[int, int] = {}
        new_leaderboard_items: list[tuple[utils.Pp, int]] = []
        new_values_by_position: list[int] = []

        async with utils.DatabaseWrapper() as db:
            records = await db("""
                SELECT *
                FROM pps
                ORDER BY pp_multiplier DESC
                """)
            next_place: utils.Pp | None = None
            for n, record in enumerate(records):
                pp_data = dict(record)
                pp = utils.Pp.from_record(pp_data)

                if n < 10:
                    new_leaderboard_items.append((pp, pp.multiplier.value))

                if next_place is None:
                    overtake_difference = 0
                else:
                    overtake_difference = (
                        next_place.multiplier.value - pp.multiplier.value
                    )

                new_position_per_user_id[record["user_id"]] = n + 1
                new_values_by_position.append(overtake_difference)
                next_place = pp

        self.positions_per_user_id = new_position_per_user_id
        self.leaderboard_items = new_leaderboard_items
        self.values_by_position = new_values_by_position

        self.logger.debug("Multiplier leaderboard cache updated")

    def podium_value_formatter(self, position: int) -> str:
        multiplier = self.leaderboard_items[position - 1][1]
        return f"**{utils.format_int(multiplier)}x** multiplier"

    def comparison_formatter(self, position: int) -> str | None:
        if position == 1:
            return

        difference = self.values_by_position[position - 1]

        return (
            f"{utils.format_int(difference)}x multiplier behind"
            f" {utils.format_ordinal(position - 1)} place"
        )


class DonationLeaderboardCache(LeaderboardCache[int, int]):
    title = "the most generous people sharing their pp with everyone"
    label = "Donations (via /donate)"

    @classmethod
    def for_guild(cls: type[Self], guild: discord.Guild) -> Self:
        leaderboard_cache = cls(
            logger=logging.getLogger(
                "vbu.bot.cog.LeaderboardCommandCog.DonationLeaderboardCache"
                f"-GUILD-{guild.id}"
            ),
        )

        leaderboard_cache.title = (
            "the most generous server members sharing their pp with everyone"
        )

        async def guild_update():
            leaderboard_cache.logger.debug("Updating donation leaderboard cache...")

            new_position_per_user_id: dict[int, int] = {}
            new_leaderboard_items: list[tuple[utils.Pp, int]] = []
            new_values_by_position: list[int] = []

            async with utils.DatabaseWrapper() as db:
                records = await db(
                    """
                    WITH donation_totals AS (
                        SELECT
                            donor_id,
                            SUM(amount) AS total_donations
                        FROM donations
                        INNER JOIN pp_guilds ON
                            pp_guilds.user_id=donations.donor_id
                            AND pp_guilds.guild_id=$1 
                        GROUP BY donor_id
                    )
                    SELECT
                        pps.*,
                        donation_totals.total_donations
                    FROM donation_totals
                    JOIN pps
                        ON donation_totals.donor_id = pps.user_id
                    ORDER BY donation_totals.total_donations DESC
                    """,
                    guild.id,
                )
                next_place_total_donations = 0

                for n, record in enumerate(records):
                    pp_data = dict(record)
                    total_donations = pp_data.pop("total_donations")

                    if n < 10:
                        pp = utils.Pp.from_record(pp_data)
                        new_leaderboard_items.append((pp, total_donations))

                    new_position_per_user_id[record["user_id"]] = n + 1
                    new_values_by_position.append(
                        next_place_total_donations - total_donations
                    )

                    next_place_total_donations = total_donations

            leaderboard_cache.positions_per_user_id = new_position_per_user_id
            leaderboard_cache.leaderboard_items = new_leaderboard_items
            leaderboard_cache.values_by_position = new_values_by_position

            leaderboard_cache.logger.debug("Donation leaderboard cache updated")

        leaderboard_cache.update = guild_update

        return leaderboard_cache

    async def update(self) -> None:
        self.logger.debug("Updating donation leaderboard cache...")

        new_position_per_user_id: dict[int, int] = {}
        new_leaderboard_items: list[tuple[utils.Pp, int]] = []
        new_values_by_position: list[int] = []

        async with utils.DatabaseWrapper() as db:
            records = await db("""
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
                """)
            next_place_total_donations = 0

            for n, record in enumerate(records):
                pp_data = dict(record)
                total_donations = pp_data.pop("total_donations")

                if n < 10:
                    pp = utils.Pp.from_record(pp_data)
                    new_leaderboard_items.append((pp, total_donations))

                new_position_per_user_id[record["user_id"]] = n + 1
                new_values_by_position.append(
                    next_place_total_donations - total_donations
                )

                next_place_total_donations = total_donations

        self.positions_per_user_id = new_position_per_user_id
        self.leaderboard_items = new_leaderboard_items
        self.values_by_position = new_values_by_position

        self.logger.debug("Donation leaderboard cache updated")

    def podium_value_formatter(self, position: int) -> str:
        amount = self.leaderboard_items[position - 1][1]
        return f"{utils.format_inches(amount)} donated"

    def comparison_formatter(self, position: int) -> str | None:
        if position == 1:
            return

        difference = self.values_by_position[position - 1]

        return (
            f"{utils.format_int(difference)} in donations behind"
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

        current_category = "SIZE"
        current_scope = "GLOBAL"
        leaderboard_cache = self.CATEGORIES[current_category]

        embed = leaderboard_cache.generate_embed(ctx)

        interaction_id = uuid.uuid4().hex
        category_menu = discord.ui.SelectMenu(
            custom_id=f"{interaction_id}_CATEGORY",
            options=[
                discord.ui.SelectOption(
                    label=leaderboard_cache.label,
                    value=category,
                    default=category == current_category,
                )
                for category, leaderboard_cache in self.CATEGORIES.items()
            ],
        )

        if ctx.guild is not None:
            guild = cast(discord.Guild, ctx.guild)

            scope_menu = discord.ui.SelectMenu(
                custom_id=f"{interaction_id}_SCOPE",
                options=[
                    discord.ui.SelectOption(
                        label="Worldwide",
                        value="GLOBAL",
                        description="the biggest pps in the universe",
                        emoji="🌍",
                        default=True,
                    ),
                    discord.ui.SelectOption(
                        label=utils.limit_text(guild.name, 80),
                        value="GUILD",
                        description="only the pps in this server",
                        emoji="👑",
                        default=False,
                    ),
                ],
            )

            components = discord.ui.MessageComponents(
                discord.ui.ActionRow(category_menu), discord.ui.ActionRow(scope_menu)
            )

        else:
            components = discord.ui.MessageComponents(
                discord.ui.ActionRow(category_menu)
            )

        await ctx.interaction.response.send_message(
            embed=embed,
            components=components,
        )

        while True:
            try:
                interaction, action = await utils.wait_for_component_interaction(
                    self.bot,
                    interaction_id,
                    users=[ctx.author],
                    actions=["CATEGORY", "SCOPE"],
                    timeout=120,
                )
            except asyncio.TimeoutError:
                components.disable_components()
                try:
                    await ctx.interaction.edit_original_message(components=components)
                except discord.HTTPException:
                    pass
                break

            if action == "CATEGORY":
                current_category = interaction.values[0]
                for option in category_menu.options:
                    option.default = option.value == current_category
            elif ctx.guild is not None:
                current_scope = cast(LeaderboardScope, interaction.values[0])

                # get scope_menu the hard way cause its pOsSiBlY uNbOuNd
                scope_menu_row = cast(discord.ui.ActionRow, components.components[1])
                scope_menu = cast(discord.ui.SelectMenu, scope_menu_row.components[0])

                for option in scope_menu.options:
                    option.default = option.value == current_scope

            leaderboard_cache = self.CATEGORIES[current_category]

            if current_scope == "GUILD" and ctx.guild is not None:
                guild = cast(discord.Guild, ctx.guild)
                leaderboard_cache = leaderboard_cache.for_guild(guild)
                await leaderboard_cache.update()

            embed = leaderboard_cache.generate_embed(ctx)

            await interaction.response.edit_message(embed=embed, components=components)


async def setup(bot: utils.Bot):
    await bot.add_cog(LeaderboardCommandCog(bot))
