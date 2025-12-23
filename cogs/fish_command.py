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
            list(cls), weights=list(activity.value for activity in cls)
        )[0]


MinigameActivity = Literal[Activity.CLICK_THAT_BUTTON_MINIGAME]


class ChristmasActivity(enum.Enum):
    SUCCESS = 0.7
    ROD_BREAK = 0.1
    FILL_IN_THE_BLANK_MINIGAME = 0.2 / 4
    REVERSE_MINIGAME = 0.2 / 4
    REPEAT_MINIGAME = 0.2 / 4
    CLICK_THAT_BUTTON_MINIGAME = 0.2 / 4

    @classmethod
    def random(cls):
        return random.choices(
            list(cls), weights=list(activity.value for activity in cls)
        )[0]


ChristmasMinigameActivity = Literal[
    ChristmasActivity.FILL_IN_THE_BLANK_MINIGAME,
    ChristmasActivity.REVERSE_MINIGAME,
    ChristmasActivity.REPEAT_MINIGAME,
    ChristmasActivity.FILL_IN_THE_BLANK_MINIGAME,
]


class FishCommandCog(vbu.Cog[utils.Bot]):
    # Things you can catch while fishing, in order of best to worst.
    DEFAULT_CATCHES: list[str] = [
        "an old rusty can",
        "a little tiny stupid dumb fish",
        "a fish",
        "a big fish",
        "a REALLY big fish",
    ]

    CHRISTMAS_CATCHES: list[str] = [
        "an soggy candy cane <a:CANDY_CANE:1452409272112513156>",
        "a frozen fish",
        "a lot of candy",
        "Santa's sack o' gifts",
        "Santa's underwear (YUMMY)",
        "SANTAS (used) DILDO",
    ]

    ROD_BREAK_RESPONSES: list[str] = [
        "{} flung their fishing rod too hard and it broke lmaoooo",
        "{} accidentally threw their fishing rod in the water lmao what a fucking loser",
    ]

    def __init__(self, bot: Bot, logger_name: str | None = None):
        super().__init__(bot, logger_name)

    async def start_minigame(
        self,
        minigame_activity: MinigameActivity | ChristmasMinigameActivity,
        *,
        bot: utils.Bot,
        connection: asyncpg.Connection,
        pp: utils.Pp,
        interaction: discord.Interaction,
    ):
        minigame_types: dict[Activity | ChristmasActivity, type[utils.Minigame]] = {
            Activity.CLICK_THAT_BUTTON_MINIGAME: utils.ClickThatButtonMinigame,
            ChristmasActivity.FILL_IN_THE_BLANK_MINIGAME: utils.FillInTheBlankMinigame,
            ChristmasActivity.REVERSE_MINIGAME: utils.ReverseMinigame,
            ChristmasActivity.REPEAT_MINIGAME: utils.RepeatMinigame,
            ChristmasActivity.FILL_IN_THE_BLANK_MINIGAME: utils.FillInTheBlankMinigame,
        }

        minigame_type = minigame_types[minigame_activity]
        minigame = minigame_type(
            bot=bot,
            connection=connection,
            pp=pp,
            context=minigame_type.generate_random_dialogue("fish"),
            channel=interaction.channel,
        )

        await minigame.start(interaction)

    def get_catch(self, worth: float) -> str:
        if utils.MinigameDialogueManager.variant == "christmas":
            catches = self.CHRISTMAS_CATCHES
        else:
            catches = self.DEFAULT_CATCHES

        worth_index = round(worth * (len(catches) - 1))
        fishing_catch = catches[worth_index]

        # avoid different behaviour for different worths with the same fishing_catch value
        worth = worth_index / (len(catches) - 1)
        print(worth)

        if worth > 0.8:
            return f"**[{fishing_catch}](<{utils.MEME_URL}>)**"

        if worth > 0.5:
            return f"**{fishing_catch}**"

        return fishing_catch

    @commands.command(
        "fish",
        utils.Command,
        category=utils.CommandCategory.GROWING_PP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @utils.Command.tiered_cooldown(
        default=60,
        voter=30,
    )
    @commands.is_slash_command()
    async def fish_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Go fishing for some inches! Don't question it!
        """

        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, "You're still busy fishing!"
            ),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)
            tool = utils.ItemManager.get_command_tool("fish")

            if not await utils.InventoryItem.user_has_item(
                db.conn, ctx.author.id, tool.id
            ):
                raise utils.MissingTool(tool=tool)

            if utils.MinigameDialogueManager.variant == "christmas":
                activity = ChristmasActivity.random()
            else:
                activity = Activity.random()

            if activity.name.endswith("_MINIGAME"):
                activity = cast(MinigameActivity | ChristmasMinigameActivity, activity)
                await self.start_minigame(
                    activity,
                    bot=self.bot,
                    connection=db.conn,
                    pp=pp,
                    interaction=ctx.interaction,
                )
                return

            embed = utils.Embed()

            if utils.MinigameDialogueManager.variant == "christmas":
                embed.set_author(name="❄️🎣 north pole fishing")

            if activity in [Activity.ROD_BREAK, ChristmasActivity.ROD_BREAK]:
                inv_tool = await utils.InventoryItem.fetch(
                    db.conn,
                    {"user_id": ctx.author.id, "id": tool.id},
                    lock=utils.RowLevelLockMode.FOR_UPDATE,
                )
                inv_tool.amount.value -= 1
                await inv_tool.update(db.conn)

                embed.colour = utils.RED
                embed.description = random.choice(self.ROD_BREAK_RESPONSES).format(
                    ctx.author.mention
                ) + (
                    f"\n\n(You now have {inv_tool.format_item(article=utils.Article.NUMERAL)}"
                    " left)"
                )

                if inv_tool.amount.value == 0:
                    embed.description += " 😢"

            elif activity in [Activity.SUCCESS, ChristmasActivity.SUCCESS]:
                growth = random.randint(1, 15)
                pp.grow_with_multipliers(
                    growth, voted=await pp.has_voted(), channel=ctx.channel
                )

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


async def setup(bot: utils.Bot):
    await bot.add_cog(FishCommandCog(bot))
