import enum
import random
from typing import Literal, cast

import asyncpg
import discord
from discord.ext import commands, vbu

from cogs.utils.bot import Bot

from . import utils


class Activity(enum.Enum):
    SUCCESS = 0.6
    SHOVEL_BREAK = 0.3
    CLICK_THAT_BUTTON_MINIGAME = 0.1

    @classmethod
    def random(cls):
        return random.choices(
            list(Activity), weights=list(activity.value for activity in Activity)
        )[0]


MinigameActivity = Literal[Activity.CLICK_THAT_BUTTON_MINIGAME]


class DigCommandCog(vbu.Cog[utils.Bot]):
    SHOVEL_BREAK_RESPONSES: list[str] = [
        "{} broke their shovel while trying to shovel through bedrock",
        "{}'s shovel literally snapped in half while trying to dig",
        "{}'s shovel shattered into a thousand pieces",
    ]

    def __init__(self, bot: Bot, logger_name: str | None = None):
        super().__init__(bot, logger_name)

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
    # @commands.cooldown(1, 10, commands.BucketType.user)
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
                raise commands.CheckFailure(
                    f"You need a **{tool.name}** for this command!"
                    f" You can buy one in the {utils.format_slash_command('shop')}"
                )

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

            if activity in {Activity.SUCCESS, Activity.SHOVEL_BREAK}:
                embed = utils.Embed()
                embeds.append(embed)

                growth = random.randint(1, 15)
                pp.grow_with_multipliers(growth)

                embed.colour = utils.GREEN
                embed.description = (
                    f"**{ctx.author.mention}** went digging"
                    f" and found {pp.format_growth()}!"
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
                    embed.description = (
                        random.choice(self.SHOVEL_BREAK_RESPONSES).format(
                            ctx.author.mention
                        )
                        + f"\n\n(You now have {inv_tool.format_item()} left)"
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
