import asyncio
import random
import uuid
from datetime import datetime, UTC

import asyncpg
import discord
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

    async def give(self, conn: asyncpg.Connection, pp: utils.Pp) -> None:
        if self.multiplier:
            pp.multiplier.value += self.multiplier
        for item_key, amount in self.items.items():
            item = utils.InventoryItem(pp.user_id, item_key, amount)
            await item.update(conn, ensure_difference=False, additional=True)


class DailyCommandCog(vbu.Cog[utils.Bot]):
    MIN_DAILY_GROWTH = 240
    MAX_DAILY_GROWTH = 260
    STREAK_REWARDS: dict[int, StreakReward] = {
        3: StreakReward(
            items={
                "FISHING_ROD": 10,
                "RIFLE": 10,
                "SHOVEL": 10,
            }
        ),
        10: StreakReward(
            multiplier=5,
            items={
                "FISHING_ROD": 50,
                "RIFLE": 50,
                "SHOVEL": 50,
            },
        ),
        25: StreakReward(
            multiplier=20,
            items={
                "FISHING_ROD": 1000,
                "RIFLE": 500,
                "SHOVEL": 250,
            },
        ),
        50: StreakReward(
            multiplier=50,
            items={
                "FISHING_ROD": 10000,
                "RIFLE": 2500,
                "SHOVEL": 500,
                "GOLDEN_COIN": 10,
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
        self,
        pp: utils.Pp,
        channel: utils.InteractionChannel | str | None,
        streak: int,
        voted: bool,  # to avoid double-fetching
        *,
        connection: asyncpg.Connection,
    ) -> str:
        reward_message_chunks: list[str] = []

        pp.grow_with_multipliers(
            random.randint(
                DailyCommandCog.MIN_DAILY_GROWTH, DailyCommandCog.MAX_DAILY_GROWTH
            ),
            voted=voted,
            channel=channel,
        )
        reward_message_chunks.append(pp.format_growth())
        await pp.update(connection)

        if streak in self.STREAK_REWARDS:
            streak_reward = self.STREAK_REWARDS[streak]
            for item_id, amount in streak_reward.items.items():
                reward_item = utils.InventoryItem(pp.user_id, item_id, amount)
                await reward_item.update(connection, additional=True)
                reward_message_chunks.append(
                    reward_item.format_item(article=utils.Article.INDEFINITE)
                )

        return utils.format_iterable(reward_message_chunks, inline=True)

    def get_next_streak_reward(self, streak: int) -> tuple[StreakReward, int]:
        """Returns `(next_streak_reward: StreakReward, required_streak: int)`"""
        max_streak = list(self.STREAK_REWARDS)[-1]

        if streak >= max_streak:
            required_streak = (
                streak // self.LOOP_STREAK_REWARD + 1
            ) * self.LOOP_STREAK_REWARD
            next_streak_award = self.STREAK_REWARDS[self.LOOP_STREAK_REWARD]
            return next_streak_award, required_streak

        for required_streak, streak_award in self.STREAK_REWARDS.items():
            if streak < required_streak:
                return streak_award, required_streak

        raise ValueError

    async def not_voted_handler(
        self, ctx: commands.SlashContext[utils.Bot], pp: utils.Pp
    ) -> discord.ComponentInteraction | None:
        """Returns `continue_without_voting: bool`"""
        embed = utils.Embed(utils.RED)
        embed.title = random.choice(
            [
                f"ur missing out on a lot of pp!!!!",
                f"ur about to waste so many inches",
            ]
        )

        multiplier, _, _ = pp.get_full_multiplier(voted=True, channel=ctx.channel)
        max_growth = self.MAX_DAILY_GROWTH * multiplier
        embed.description = (
            f"{ctx.author.mention} You haven't voted yet bro!!!!"
            " that means you'll be missing out on up to"
            f" {utils.format_inches(max_growth)}**!!!!!!**"
            "\n\n Voting also allows you to run this command **TWICE A DAY!!!!**"
            f"\n\n not worth it twin. **[VOTE!!!!!]({utils.VOTE_URL})**"
        )

        interaction_id = uuid.uuid4().hex

        components = discord.ui.MessageComponents(
            discord.ui.ActionRow(
                discord.ui.Button(
                    label="I'll come back after voting :)",
                    custom_id=f"{interaction_id}_CANCEL",
                    style=discord.ButtonStyle.green,
                ),
                discord.ui.Button(
                    label="Nah. I hate free stuff.",
                    custom_id=f"{interaction_id}_PROCEED",
                    style=discord.ButtonStyle.red,
                ),
            )
        )

        vote_components = discord.ui.MessageComponents(
            discord.ui.ActionRow(
                discord.ui.Button(
                    label="vote!! (infinity dih button)",
                    style=discord.ButtonStyle.url,
                    url=utils.VOTE_URL,
                )
            )
        )

        await ctx.interaction.response.send_message(
            embed=embed,
            components=components,
        )

        try:
            component_interaction, action = await utils.wait_for_component_interaction(
                self.bot,
                interaction_id,
                users=[ctx.author],
                actions=["CANCEL", "PROCEED"],
                timeout=15,
            )
        except asyncio.TimeoutError:
            assert isinstance(ctx.command, utils.Command)
            await ctx.command.async_reset_cooldown(ctx)

            embed = utils.Embed(utils.RED)
            embed.title = "You've been idle for a while so this command got cancelled"
            embed.url = utils.VOTE_URL
            embed.description = (
                "i assume you went off to vote or something."
                f"\n\nif you didn't - **[VOTE NOW!!!1!!!!]({utils.VOTE_URL})**"
            )

            try:
                await ctx.interaction.edit_original_message(
                    embed=embed,
                    components=vote_components,
                )
            except discord.HTTPException:
                pass

            return None

        if action == "CANCEL":
            assert isinstance(ctx.command, utils.Command)

            await ctx.command.async_reset_cooldown(ctx)

            embed.color = utils.GREEN
            embed.title = f"{':face_holding_back_tears:'*3} thank u"
            embed.url = utils.VOTE_URL

            embed.description = (
                f"awesome!! you can vote by clicking **[here]({utils.VOTE_URL})**,"
                f" **[here]({utils.VOTE_URL})** or **[here]({utils.VOTE_URL})**."
                f" or maybe even **[here]({utils.VOTE_URL})**."
                f" and if you're reaaaalllyyy feeling frisky,"
                f" you could even click **[here]({utils.VOTE_URL})**."
                " or the little button down below. all up to you :))"
                f"\n\n **Run {utils.format_slash_command('daily')} again"
                " when you're back!**"
            )
            try:
                await component_interaction.response.edit_message(
                    embed=embed,
                    components=vote_components,
                )
            except discord.HTTPException:
                pass

            return None

        return component_interaction

    @commands.command(
        "daily",
        utils.Command,
        category=utils.CommandCategory.GROWING_PP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @utils.Command.tiered_cooldown(
        default=60 * 60 * 24,
        # default=0,
        voter=commands.Cooldown(2, 60 * 60 * 24),
    )
    @commands.is_slash_command()
    async def daily_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Collect your daily reward!
        """

        continue_without_voting_interaction: discord.ComponentInteraction | None = None
        voted = await vbu.user_has_voted(ctx.author.id)

        if not voted:
            async with utils.DatabaseWrapper() as db:
                pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id)

            continue_without_voting_interaction = await self.not_voted_handler(ctx, pp)

            if not continue_without_voting_interaction:
                return

        # double fetch in case of changes while in not_voted_handler state
        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, f"You're still busy collecting your daily reward!"
            ),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)
            voted = await pp.has_voted()
            streaks = await utils.Streaks.fetch_from_user(
                db.conn, ctx.author.id, edit=True
            )

            # store daily_expired as the property might change values throughout the
            # span of the command
            daily_expired = streaks.daily_expired

            streaks.last_daily.value = datetime.now(UTC).replace(tzinfo=None)

            if daily_expired:
                streaks.daily.value = 1
            else:
                streaks.daily.value += 1

            await streaks.update(db.conn)

            reward_message = await self.give_reward(
                pp, ctx.channel, streaks.daily.value, voted, connection=db.conn
            )

            embed = utils.Embed()

            if daily_expired:
                embed.title = f"Streak lost :( Back to day 1"
            else:
                embed.title = f"Day {streaks.daily.value} streak 🔥"

            embed.colour = utils.PINK
            embed.description = f"{ctx.author.mention}, you received {reward_message}!"

            if streaks.daily.value in self.STREAK_REWARDS:
                embed.description = (
                    f"[**STREAK BONUS!**]({utils.MEME_URL}) {embed.description}"
                )
                reward = self.STREAK_REWARDS[streaks.daily.value]
                await reward.give(db.conn, pp)

            _, next_streak = self.get_next_streak_reward(streaks.daily.value)
            days_left = next_streak - streaks.daily.value

            embed.description += (
                f"\n\nYour next streak bonus is in **{days_left}**"
                f" day{'' if days_left == 1 else 's'}"
                " <a:patpp:914593683091894283>"
            )

            embed.add_tip()

            if continue_without_voting_interaction is None:
                await ctx.interaction.response.send_message(embed=embed)
                return

            embed.set_footer(text="you should've voted lil bro")

            interaction = continue_without_voting_interaction

            try:
                await interaction.response.edit_message(
                    embed=embed,
                    components=None,
                )
                return
            except discord.HTTPException:
                await interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(DailyCommandCog(bot))
