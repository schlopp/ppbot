import random

import asyncpg
from discord.ext import commands, vbu

from . import utils


class StreakReward(utils.Object):
    __slots__ = ("multiplier", "note", "items")

    def __init__(
        self,
        *,
        multiplier: int | None = None,
        note: str | None = None,
        items: dict[str, int],
    ) -> None:
        self.multiplier = multiplier
        self.note = note
        self.items = items


class DailyCommandCog(vbu.Cog[utils.Bot]):
    MIN_DAILY_GROWTH = 90
    MAX_DAILY_GROWTH = 110
    STREAK_REWARDS: dict[int, StreakReward] = {
        3: StreakReward(
            items={
                "FISHING_ROD": 5,
            }
        ),
        10: StreakReward(
            multiplier=5,
            items={
                "FISHING_ROD": 20,
                "RIFLE": 10,
            },
        ),
        25: StreakReward(
            multiplier=20,
            items={
                "FISHING_ROD": 100,
                "RIFLE": 50,
                "SHOVEL": 25,
            },
        ),
        50: StreakReward(
            multiplier=50,
            items={
                "FISHING_ROD": 500,
                "RIFLE": 250,
                "SHOVEL": 100,
            },
        ),
        69: StreakReward(
            items={
                "GOLDEN_COIN": 420,
                "COOKIE": 6969,
            },
        ),
    }
    LOOP_STREAK_REWARD = 50

    async def give_reward(
        self, pp: utils.Pp, streak: int, *, connection: asyncpg.Connection
    ) -> str:
        reward_message_chunks: list[str] = []

        pp.grow(
            random.randint(
                DailyCommandCog.MIN_DAILY_GROWTH, DailyCommandCog.MAX_DAILY_GROWTH
            )
        )
        reward_message_chunks.append(pp.format_growth())
        await pp.update(connection)

        if streak in self.STREAK_REWARDS:
            streak_reward = self.STREAK_REWARDS[streak]
            for item_id, amount in streak_reward.items.items():
                reward_item = utils.InventoryItem(pp.user_id, item_id, amount)
                await reward_item.update(connection, additional=True)
                reward_message_chunks.append(reward_item.format_item())

        return utils.format_iterable(reward_message_chunks, inline=True)

    def get_next_streak_reward(self, streak: int) -> tuple[StreakReward, int]:
        """Returns `(next_streak_reward: StreakReward, required_streak: int)`"""
        max_streak = list(self.STREAK_REWARDS)[-1]

        if streak >= max_streak:
            required_streak = streak // self.LOOP_STREAK_REWARD + 1
            next_streak_award = self.STREAK_REWARDS[self.LOOP_STREAK_REWARD]
            return next_streak_award, required_streak

        for required_streak, streak_award in self.STREAK_REWARDS.items():
            if streak < required_streak:
                return streak_award, required_streak

        raise ValueError

    @commands.command(
        "daily",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.cooldown(1, 60 * 60 * 24, commands.BucketType.user)
    @commands.is_slash_command()
    async def daily_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Collect your daily reward!
        """
        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, f"You're still busy collecting your daily reward!"
            ),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)
            streaks = await utils.Streaks.fetch_from_user(
                db.conn, ctx.author.id, edit=True
            )
            streaks.daily.value += 1
            await streaks.update(db.conn)

            reward_message = await self.give_reward(
                pp, streaks.daily.value, connection=db.conn
            )

            embed = utils.Embed()
            embed.title = f"Day {streaks.daily.value} streak 🔥"
            embed.colour = utils.PINK
            embed.description = f"{ctx.author.mention}, you received {reward_message}!"

            if streaks.daily.value in self.STREAK_REWARDS:
                embed.description = (
                    f"[**STREAK BONUS!**]({utils.MEME_URL}) {embed.description}"
                )

            _, next_streak = self.get_next_streak_reward(streaks.daily.value)
            days_left = next_streak - streaks.daily.value

            embed.description += (
                f"\n\nYour next streak bonus is in **{days_left}**"
                f" day{'' if days_left == 1 else 's'}"
                " <a:patpp:914593683091894283>"
            )

            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)


def setup(bot: utils.Bot):
    bot.add_cog(DailyCommandCog(bot))
