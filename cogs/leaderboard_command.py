from datetime import timedelta
from discord.ext import commands, vbu, tasks

from . import utils


class LeaderboardCommandCog(vbu.Cog[utils.Bot]):
    LEADERBOARD_CACHE_REFRESH_TIME = timedelta(seconds=15)

    position_cache: dict[int, int] = {}
    size_cache: dict[int, int] = {}
    top10_cache: list[utils.Pp] = []

    def __init__(self, bot: utils.Bot, logger_name: str | None = None):
        super().__init__(bot, logger_name)
        self.cache_leaderboard.start()

    async def cog_unload(self) -> None:
        self.cache_leaderboard.cancel()

    @tasks.loop(seconds=15)
    async def cache_leaderboard(self) -> None:
        self.logger.debug("Updating leaderboard cache...")

        new_top10_cache: list[utils.Pp] = []
        new_position_cache: dict[int, int] = {}
        new_size_cache: dict[int, int] = {}

        async with utils.DatabaseWrapper() as db:
            records = await db(
                """
                SELECT
                    *,
                    ROW_NUMBER()
                    OVER (
                        ORDER BY pp_size
                        DESC
                    )
                    AS position 
                FROM pps
                """
            )
            for n, record in enumerate(records):
                if n < 10:
                    pp_data = dict(record)
                    pp_data.pop("position")
                    new_top10_cache.append(utils.Pp.from_record(pp_data))
                new_position_cache[record["user_id"]] = record["position"]
                new_size_cache[record["position"]] = record["pp_size"]

        self.top10_cache = new_top10_cache
        self.position_cache = new_position_cache
        self.size_cache = new_size_cache

        self.logger.debug("Leaderboard cache updated")

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

        embed = utils.Embed()
        embed.set_author(
            name=(
                "the biggest pps in the entire universe"
                f" • updates every {utils.format_time(self.LEADERBOARD_CACHE_REFRESH_TIME)}"
            ),
            url=utils.MEME_URL,
        )

        better_pp_size: int | None = None

        position = self.position_cache.get(ctx.author.id)

        if position is not None and position != 1:
            better_pp_size = self.size_cache[position - 1]

        segments: list[str] = []

        if position is not None:
            pp_size = self.size_cache[position]

            if better_pp_size is not None:
                difference = better_pp_size - pp_size

                embed.set_footer(
                    text=(
                        f"ur {utils.format_ordinal(position)} place on the leaderboard,"
                        f" {utils.format_int(difference)} inches"
                        f" behind {utils.format_ordinal(position - 1)} place"
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

        for position, pp in enumerate(self.top10_cache, start=1):
            if position <= 3:
                prefix = ["🥇", "🥈", "🥉"][position - 1]
            elif position == 10:
                prefix = "<a:nerd:1244646167799791637>"
            else:
                prefix = "🔹"

            segments.append(
                f"{prefix} **{utils.format_int(pp.size.value)} inches**"
                f" - {pp.name.value} `({pp.user_id})`"
            )

        embed.description = "\n".join(segments)

        await ctx.interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(LeaderboardCommandCog(bot))
