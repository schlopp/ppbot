from dataclasses import dataclass
import enum
import itertools
import math
import random
from typing import Literal, cast

import asyncpg
import discord
from discord.ext import commands, vbu

from cogs.utils.bot import Bot

from . import utils


class Activity(enum.Enum):
    SUCCESS_GROW = 0.55
    SUCCESS_MULTIPLIER = 0.05
    SHOVEL_BREAK = 0.3
    CLICK_THAT_BUTTON_MINIGAME = 0.1

    @classmethod
    def random(cls):
        return random.choices(
            list(Activity), weights=list(activity.value for activity in Activity)
        )[0]


@dataclass
class DepthReward:
    name: str
    name_plural: str
    name_stylised: str
    growth_range: tuple[int, int]
    max_item_value: int


class DepthRewardType(enum.Enum):
    COOL_BOX = DepthReward(
        "cool box of stuff", "cool boxes of stuff", "cool box of stuff :)", (1, 10), 5
    )
    TREASURE_CHEST = DepthReward(
        "treasure chest", "treasure chests", "treasure chest!", (10, 30), 20
    )
    AWESOME_TREASURE_CHEST = DepthReward(
        "SUPER MEGA AWESOME TREASURE CHEST",
        "SUPER MEGA AWESOME TREASURE CHESTS",
        "SUPER MEGA AWESOME TREASURE CHEST!!",
        (30, 60),
        45,
    )
    GIFT_FROM_THE_PP_GODS = DepthReward(
        "<:ppEvil:902894209160347708> gift from the pp gods <:ppEvil:902894209160347708>",
        "<:ppEvil:902894209160347708> gifts from the pp gods <:ppEvil:902894209160347708>",
        "gifts from the pp gods",
        (60, 90),
        75,
    )


MinigameActivity = Literal[Activity.CLICK_THAT_BUTTON_MINIGAME]


class DigCommandCog(vbu.Cog[utils.Bot]):
    SHOVEL_BREAK_RESPONSES: list[str] = [
        "{} broke their shovel while trying to shovel through bedrock",
        "{}'s shovel literally snapped in half while trying to dig",
        "{}'s shovel shattered into a thousand pieces",
    ]
    UNIQUE_DEPTH_REWARDS: dict[int, DepthRewardType] = {
        69: DepthRewardType.GIFT_FROM_THE_PP_GODS,
        420: DepthRewardType.GIFT_FROM_THE_PP_GODS,
        666: DepthRewardType.GIFT_FROM_THE_PP_GODS,
        6969: DepthRewardType.GIFT_FROM_THE_PP_GODS,
    }

    def __init__(self, bot: Bot, logger_name: str | None = None):
        super().__init__(bot, logger_name)

    def _get_depth_reward(self, depth: int) -> DepthRewardType | None:
        try:
            return self.UNIQUE_DEPTH_REWARDS[depth]
        except:
            pass

        if depth == 10:
            return DepthRewardType.COOL_BOX
        elif depth % 1000 == 0:
            return DepthRewardType.GIFT_FROM_THE_PP_GODS
        elif depth % 100 == 0:
            return DepthRewardType.AWESOME_TREASURE_CHEST
        elif depth % 25 == 0:
            return DepthRewardType.TREASURE_CHEST

    def _get_depth_rewards(
        self, depth_range: range
    ) -> dict[int, DepthRewardType] | None:
        rewards: dict[int, DepthRewardType] = {}

        for depth in depth_range:
            try:
                rewards[depth] = self.UNIQUE_DEPTH_REWARDS[depth]
            except:
                pass

            if depth == 10:
                rewards[depth] = DepthRewardType.COOL_BOX
            elif depth % 1000 == 0:
                rewards[depth] = DepthRewardType.GIFT_FROM_THE_PP_GODS
            elif depth % 100 == 0:
                rewards[depth] = DepthRewardType.AWESOME_TREASURE_CHEST
            elif depth % 25 == 0:
                rewards[depth] = DepthRewardType.TREASURE_CHEST

        if not rewards:
            return None

        return dict(sorted(rewards.items()))

    def _generate_reward_visual(self, pp: utils.Pp) -> str:
        unformatted_segments: list[tuple[str, str]] = []

        if pp.digging_depth.value % 5 == 0:
            closest_standard_depth = pp.digging_depth.value + 5
        else:
            closest_standard_depth = math.ceil(pp.digging_depth.value / 5) * 5
        closest_depth = closest_standard_depth
        future_rewards: dict[int, DepthRewardType] = {}

        rewards_before_closest_depth = self._get_depth_rewards(
            range(pp.digging_depth.value + 1, closest_standard_depth)
        )
        if rewards_before_closest_depth:
            closest_depth = next(iter(rewards_before_closest_depth))
            future_rewards.update(rewards_before_closest_depth)

        for depth in itertools.count(closest_depth):
            if len(unformatted_segments) >= 4:
                break

            depth_segment = utils.format_int(
                depth, format_type=utils.IntFormatType.FULL
            )
            depth_segment = f"{depth_segment} ft"
            if depth in future_rewards:
                segment = f"{{}} [{future_rewards[depth].name}]"
                unformatted_segments.append((depth_segment, segment))
                continue

            reward = self._get_depth_reward(depth)
            if reward:
                segment = f"{{}} [{reward.value.name_stylised}]"
                unformatted_segments.append((depth_segment, segment))
                continue

            if depth % 5 == 0:
                segment = f"{{}} ..."
                unformatted_segments.append((depth_segment, segment))
                continue

        max_depth_segment_len = max(
            len(depth_segment) for depth_segment, _ in unformatted_segments
        )
        segments = [
            segment.format(f"{depth_segment:<{max_depth_segment_len}}")
            for depth_segment, segment in unformatted_segments
        ]

        formatted_depth = utils.format_int(
            pp.digging_depth.value, format_type=utils.IntFormatType.FULL
        )
        segment = f"{f'{formatted_depth} ft':<{max_depth_segment_len}} (you are here!)"
        return f"```css\n{segment}\n\n" + "\n".join(segments) + "```"

    async def start_minigame(
        self,
        minigame_activity: MinigameActivity,
        *,
        bot: utils.Bot,
        connection: asyncpg.Connection,
        pp: utils.Pp,
        interaction: discord.Interaction,
    ):
        minigame_types: dict[Activity, type[utils.Minigame]] = {
            Activity.CLICK_THAT_BUTTON_MINIGAME: utils.ClickThatButtonMinigame,
        }

        minigame_type = minigame_types[minigame_activity]
        minigame = minigame_type(
            bot=bot,
            connection=connection,
            pp=pp,
            context=minigame_type.generate_random_dialogue("dig"),
        )

        await minigame.start(interaction)

    @commands.command(
        "dig",
        utils.Command,
        category=utils.CommandCategory.GROWING_PP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @utils.Command.tiered_cooldown(
        default=60,
        voter=30,
    )
    @commands.is_slash_command()
    async def dig_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Dig down deep for some seggsy rewards
        """

        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, "You're still busy digging!"
            ),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)
            tool = utils.ItemManager.get_command_tool("dig")

            if not await utils.InventoryItem.user_has_item(
                db.conn, ctx.author.id, tool.id
            ):
                raise utils.MissingTool(tool=tool)

            activity = Activity.random()

            if activity.name.endswith("_MINIGAME"):
                activity = cast(MinigameActivity, activity)
                await self.start_minigame(
                    activity,
                    bot=self.bot,
                    connection=db.conn,
                    pp=pp,
                    interaction=ctx.interaction,
                )
                return

            embeds = []

            if activity in {
                Activity.SUCCESS_GROW,
                Activity.SUCCESS_MULTIPLIER,
                Activity.SHOVEL_BREAK,
            }:
                embed = utils.Embed()
                embeds.append(embed)

                depth = random.randint(1, 3)
                pp.digging_depth.value += depth

                embed.description = (
                    f"**{ctx.author.mention}** dug another {utils.format_int(depth)} feet down"
                    f" and found {{}}"
                )

                if activity in {Activity.SUCCESS_GROW, Activity.SHOVEL_BREAK}:
                    growth = random.randint(30, 60)
                    pp.grow_with_multipliers(growth, voted=await pp.has_voted())

                    embed.colour = utils.GREEN
                    embed.description = embed.description.format(
                        f"{pp.format_growth()}!"
                    )

                elif activity == Activity.SUCCESS_MULTIPLIER:
                    increase = random.choices(
                        [5, 4, 3, 2, 1],
                        [1, 2, 4, 8, 16],
                        k=1,
                    )[0]
                    pp.multiplier.value += increase

                    embed.colour = utils.PINK
                    embed.description = embed.description.format(
                        f" a [**{utils.format_int(increase)}x multiplier!!!**]({utils.MEME_URL})"
                    )

                new_rewards = self._get_depth_rewards(
                    range(pp.digging_depth.start_value + 1, pp.digging_depth.value + 1)
                )

                embed.description += (
                    "\n\n<:shovel:1258091579843809321> You've dug"
                    f" **{utils.format_int(pp.digging_depth.value)}** feet deep in total"
                )

                if not new_rewards:
                    embed.description += ". "
                else:
                    new_rewards_compiled: dict[DepthRewardType, int] = {}
                    for reward in new_rewards.values():
                        try:
                            new_rewards_compiled[reward] += 1
                        except KeyError:
                            new_rewards_compiled[reward] = 1

                    segments = [
                        utils.format_amount(
                            reward.value.name,
                            reward.value.name_plural,
                            amount,
                            markdown=utils.MarkdownFormat.BOLD_BLUE,
                            full_markdown=True,
                        )
                        for reward, amount in new_rewards_compiled.items()
                    ]
                    embed.description += (
                        f" and found {utils.format_iterable(segments, inline=True)}."
                    )

                    segments: list[str] = []

                    for reward, amount in new_rewards_compiled.items():
                        if amount == 1:
                            message, _, _ = await utils.give_random_reward(
                                db.conn,
                                pp,
                                growth_range=reward.value.growth_range,
                                max_item_reward_price=reward.value.max_item_value,
                            )
                            segments.append(
                                f"The **[{reward.value.name}]({utils.MEME_URL})**"
                                f" contained {message}."
                            )
                            continue

                        for ordinal in range(1, amount + 1):
                            message, _, _ = await utils.give_random_reward(
                                db.conn,
                                pp,
                                growth_range=reward.value.growth_range,
                                max_item_reward_price=reward.value.max_item_value,
                            )
                            segments.append(
                                f"The {utils.format_ordinal(ordinal)}"
                                f" **[{reward.value.name}]({utils.MEME_URL})**"
                                f" contained {message}."
                            )

                    embed.description += f"\n{utils.format_iterable(segments)}\n\n"

                embed.description += (
                    f"Here are your next rewards:\n{self._generate_reward_visual(pp)}"
                )

                embed.add_tip()

                if activity == Activity.SHOVEL_BREAK:

                    inv_tool = await utils.InventoryItem.fetch(
                        db.conn,
                        {"user_id": ctx.author.id, "id": tool.id},
                        lock=utils.RowLevelLockMode.FOR_UPDATE,
                    )
                    inv_tool.amount.value -= 1
                    await inv_tool.update(db.conn)

                    embed = utils.Embed()
                    embed.colour = utils.RED
                    embed.set_author(name=f"but... your {tool.name} broke")
                    embed.description = random.choice(
                        self.SHOVEL_BREAK_RESPONSES
                    ).format(ctx.author.mention) + (
                        f"\n\n(You now have {inv_tool.format_item(article=utils.Article.NUMERAL)}"
                        " left)"
                    )

                    if inv_tool.amount.value == 0:
                        embed.description += (
                            f" 😢 better {utils.format_slash_command('buy')} a new one"
                        )

                    embeds.append(embed)

            else:
                raise ValueError(
                    f"Can't complete digging command: No handling for activity {activity!r}"
                    " available"
                )

            await pp.update(db.conn)

            await ctx.interaction.response.send_message(embeds=embeds)


async def setup(bot: utils.Bot):
    await bot.add_cog(DigCommandCog(bot))
