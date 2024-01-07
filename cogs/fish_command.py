import enum
import random
from typing import Literal, cast

import asyncpg
import discord
from discord.ext import commands, vbu

from cogs.utils.bot import Bot

from . import utils


class Activity(enum.Enum):
    SUCCESS = 0.8
    ROD_BREAK = 0.1
    CLICK_THAT_BUTTON_MINIGAME = 0.1

    @classmethod
    def random(cls):
        return random.choices(
            list(Activity), weights=list(activity.value for activity in Activity)
        )[0]


MinigameActivity = Literal[Activity.CLICK_THAT_BUTTON_MINIGAME]


class FishCommandCog(vbu.Cog[utils.Bot]):
    # Things you can catch while fishing, in order of best to worst.
    CATCHES: list[str] = [
        "an old rusty can",
        "a little tiny stupid dumb fish",
        "a fish",
        "a big fish",
        "a REALLY big fish",
    ]

    ROD_BREAK_RESPONSES: list[str] = [
        "{} flung their fishing rod too hard and it broke lmaoooo",
        "{} accidentally threw their fishing rod in the water lmao what a fucking loser",
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
            context=minigame_type.generate_random_dialogue("fish"),
        )

        await minigame.start(interaction)

    def get_catch(self, worth: float) -> str:
        worth_index = round(worth * (len(self.CATCHES) - 1))
        fishing_catch = self.CATCHES[worth_index]

        # avoid different behaviour for different worths with the same fishing_catch value
        worth = worth_index / (len(self.CATCHES) - 1)

        if worth > 0.8:
            return f"**[{fishing_catch}](<{utils.MEME_URL}>)**"

        if worth > 0.5:
            return f"**{fishing_catch}**"

        return fishing_catch

    @commands.command(
        "fish",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.is_slash_command()
    async def fish_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Go fishing for some inches! Don't question it!
        """

        async with utils.DatabaseWrapper() as db, db.conn.transaction(), utils.DatabaseTimeoutManager.notify(
            ctx.author.id, "You're still busy fishing!"
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)
            tool = utils.ItemManager.get_command_tool("fish")

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

            embed = utils.Embed()

            if activity == Activity.ROD_BREAK:
                inv_tool = await utils.InventoryItem.fetch(
                    db.conn,
                    {"user_id": ctx.author.id, "id": tool.id},
                    lock=utils.RowLevelLockMode.FOR_UPDATE,
                )
                inv_tool.amount.value -= 1
                await inv_tool.update(db.conn)

                embed.colour = utils.RED
                embed.description = (
                    random.choice(self.ROD_BREAK_RESPONSES).format(ctx.author.mention)
                    + f"\n\nYou now have {inv_tool.format_item()} left"
                )

                if inv_tool.amount.value == 0:
                    embed.description += " :("

            elif activity == Activity.SUCCESS:
                growth = random.randint(1, 15)
                pp.grow_with_multipliers(growth)

                worth = growth / 15
                catch = self.get_catch(worth)

                embed.colour = utils.GREEN
                embed.description = (
                    f"**{ctx.author.mention}** went fishing, caught"
                    f" {catch} and sold it for {pp.format_growth()}!"
                )

            else:
                raise ValueError(
                    f"Can't complete fishing command: No handling for activity {activity!r}"
                    " available"
                )

            await pp.update(db.conn)
            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)


def setup(bot: utils.Bot):
    bot.add_cog(FishCommandCog(bot))
