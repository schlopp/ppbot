import enum
import random
from typing import Literal, cast

import asyncpg
import discord
from discord.ext import commands, vbu

from cogs.utils.bot import Bot

from . import utils


class Activity(enum.Enum):
    DONATION = 0.8
    REJECTION = 0.1
    FILL_IN_THE_BLANK_MINIGAME = 0.1 / 3
    REVERSE_MINIGAME = 0.1 / 3
    REPEAT_MINIGAME = 0.1 / 3

    @classmethod
    def random(cls):
        return random.choices(
            list(Activity), weights=list(activity.value for activity in Activity)
        )[0]


MinigameActivity = Literal[
    Activity.FILL_IN_THE_BLANK_MINIGAME,
    Activity.REVERSE_MINIGAME,
    Activity.REPEAT_MINIGAME,
]


class BegCommandCog(vbu.Cog[utils.Bot]):
    RESPONSES: list[str] = [
        "ew poor",
        "don't touch my pp",
        "my wife has a bigger pp than you",
        "broke ass bitch",
        "cringe poor",
        "beg harder",
        "poor people make me scared",
        "dont touch me poor person",
        "get a job",
        "im offended",
        "no u",
        "i dont speak poor",
        "you should take a shower",
        "i love my wife... i love my wife... i love my wife..",
        "drink some water",
        "begone beggar",
        "No.",
        "no wtf?",
        'try being a little "cooler" next time',
    ]
    DONATORS: dict[str, str | list[str] | None] = {
        "obama": None,
        "roblox noob": None,
        "dick roberts": None,
        "johnny from johnny johnny yes papa": None,
        "shrek": None,
        'kae "little twink boy"': None,
        "bob": None,
        "walter": None,
        "napoleon bonaparte": None,
        "bob ross": None,
        "coco": None,
        "thanos": ["begone before i snap you", "i'll snap ur pp out of existence"],
        "don vito": None,
        "bill cosby": [
            "dude im a registered sex offender what do you want from me",
            "im too busy touching people",
        ],
        "your step-sis": "i cant give any inches right now, im stuck",
        "pp god": "begone mortal",
        "random guy": None,
        "genie": "rub me harder next time 😩",
        "the guy u accidentally made eye contact with at the urinal": "eyes on your own pp man",
        "your mom": ["you want WHAT?", "im saving my pp for your dad"],
        "ur daughter": None,
        "Big Man Tyrone": "Every 60 seconds in Africa a minute passes.",
        "speed": None,
        "catdotjs": "Meow",
    }

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
            Activity.FILL_IN_THE_BLANK_MINIGAME: utils.FillInTheBlankMinigame,
            Activity.REPEAT_MINIGAME: utils.RepeatMinigame,
            Activity.REVERSE_MINIGAME: utils.ReverseMinigame,
        }

        minigame_type = minigame_types[minigame_activity]
        minigame = minigame_type(
            bot=bot,
            connection=connection,
            pp=pp,
            context=minigame_type.generate_random_dialogue("beg"),
        )

        await minigame.start(interaction)

    @commands.command(
        "beg",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    # @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.is_slash_command()
    async def beg_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Beg for some inches
        """

        async with utils.DatabaseWrapper() as db, db.conn.transaction(), utils.DatabaseTimeoutManager.notify(
            ctx.author.id, "You're still busy begging!"
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)

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

            donator = random.choice(list(self.DONATORS))
            embed = utils.Embed()

            if activity == Activity.DONATION:
                pp.grow(random.randint(1, 15))
                embed.colour = utils.GREEN
                embed.description = (
                    f"**{donator}** donated"
                    f" {pp.format_growth(markdown=utils.MarkdownFormat.BOLD_BLUE)} inches"
                    f" to {ctx.author.mention}"
                )

            elif activity == Activity.REJECTION:
                embed.colour = utils.BLUE
                response = self.DONATORS[donator]

                if isinstance(response, list):
                    quote = random.choice(response)
                elif isinstance(response, str):
                    quote = response
                else:
                    quote = random.choice(self.RESPONSES)

                embed.description = f"**{donator}:** {quote}"

            else:
                raise ValueError(
                    f"Can't complete begging command: No handling for activity {activity!r}"
                    " available"
                )

            await pp.update(db.conn)
            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)


def setup(bot: utils.Bot):
    bot.add_cog(BegCommandCog(bot))
