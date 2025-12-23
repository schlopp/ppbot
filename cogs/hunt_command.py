import enum
import random
from dataclasses import dataclass
from typing import Literal, cast

import asyncpg
import discord
from discord.ext import commands, vbu

from cogs.utils.bot import Bot

from . import utils


class Activity(enum.Enum):
    SUCCESS = 0.8
    RIFLE_BREAK = 0.1
    CLICK_THAT_BUTTON_MINIGAME = 0.1

    @classmethod
    def random(cls):
        return random.choices(
            list(cls), weights=list(activity.value for activity in cls)
        )[0]


MinigameActivity = Literal[Activity.CLICK_THAT_BUTTON_MINIGAME]


class ChristmasActivity(enum.Enum):
    SUCCESS = 0.7
    RIFLE_BREAK = 0.1
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


@dataclass
class Dialogue:
    hunting_options: dict[str, range]
    item_break_responses: list[str]


class HuntCommandCog(vbu.Cog[utils.Bot]):
    DEFAULT_DIALOGUE = Dialogue(
        {
            "shot a homeless man": range(1, 21),
            "deadass just killed a man": range(5, 21),
            "shot up a mall": range(5, 21),
            "hijacked a fucking orphanage and sold all the kids": range(30, 51),
            "KILLED THE PP GODS": range(50, 101),
        },
        [
            "{} got arrested and their rifle got confiscated!!1!",
        ],
    )

    CHRISTMAS_DIALOGUE = Dialogue(
        {
            "shot one of Santa's elves": range(1, 21),
            "deadass just killed one of Santa's reindeer": range(5, 21),
            "shot up the christmas workshop": range(5, 21),
            "hijacked Santa's wife and children": range(30, 51),
            "KILLED SANTA AND FUCKING RUDOLPH WHAT THE FUCK WHAT THE FUCK WHAT THE FUCK": range(
                101, 201
            ),
        },
        [
            "{} got caught by the elves and their rifle got confiscated!!1!",
        ],
    )

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
            context=minigame_type.generate_random_dialogue("hunt"),
            channel=interaction.channel,
        )

        await minigame.start(interaction)

    def get_hunting_option(self) -> tuple[str, int]:
        """Returns `(hunting_option: str, growth: int)`"""
        if utils.MinigameDialogueManager.variant == "christmas":
            dialogue = self.CHRISTMAS_DIALOGUE
        else:
            dialogue = self.DEFAULT_DIALOGUE

        worth_index = random.randrange(0, len(dialogue.hunting_options))
        hunting_option = list(dialogue.hunting_options)[worth_index]
        growth = random.choice(dialogue.hunting_options[hunting_option])

        worth = worth_index / (len(dialogue.hunting_options) - 1)

        if worth > 0.8:
            return f"**[{hunting_option}](<{utils.MEME_URL}>)**", growth

        if worth > 0.5:
            return f"**{hunting_option}**", growth

        return hunting_option, growth

    @commands.command(
        "hunt",
        utils.Command,
        category=utils.CommandCategory.GROWING_PP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @utils.Command.tiered_cooldown(
        default=60,
        voter=30,
    )
    @commands.is_slash_command()
    async def hunt_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Hunt for some inches, nothing wrong with that
        """

        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, "You're still busy hunting!"
            ),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)
            tool = utils.ItemManager.get_command_tool("hunt")

            if not await utils.InventoryItem.user_has_item(
                db.conn, ctx.author.id, tool.id
            ):
                raise utils.MissingTool(tool=tool)

            if utils.MinigameDialogueManager.variant == "christmas":
                activity = ChristmasActivity.random()
                dialogue = self.CHRISTMAS_DIALOGUE
            else:
                activity = Activity.random()
                dialogue = self.DEFAULT_DIALOGUE

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
                embed.set_author(name="🎄🤑 holiday hunting")

            if activity in [Activity.RIFLE_BREAK, ChristmasActivity.RIFLE_BREAK]:
                inv_tool = await utils.InventoryItem.fetch(
                    db.conn,
                    {"user_id": ctx.author.id, "id": tool.id},
                    lock=utils.RowLevelLockMode.FOR_UPDATE,
                )
                inv_tool.amount.value -= 1
                await inv_tool.update(db.conn)

                embed.colour = utils.RED
                embed.description = random.choice(dialogue.item_break_responses).format(
                    ctx.author.mention
                ) + (
                    f"\n\n(You now have {inv_tool.format_item(article=utils.Article.NUMERAL)}"
                    " left"
                )

                if inv_tool.amount.value == 0:
                    embed.description += " 😢"

                embed.description += ")"

            elif activity in [Activity.SUCCESS, ChristmasActivity.SUCCESS]:
                option, growth = self.get_hunting_option()
                pp.grow_with_multipliers(
                    growth, voted=await pp.has_voted(), channel=ctx.channel
                )

                embed.colour = utils.GREEN
                embed.description = (
                    f"**{ctx.author.mention}** {option} and took {pp.format_growth()}!"
                )

            else:
                raise ValueError(
                    f"Can't complete hunting command: No handling for activity {activity!r}"
                    " available"
                )

            await pp.update(db.conn)
            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(HuntCommandCog(bot))
