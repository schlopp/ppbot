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
    DONATION = 0.8
    REJECTION = 0.1
    FILL_IN_THE_BLANK_MINIGAME = 0.1 / 3
    REVERSE_MINIGAME = 0.1 / 3
    REPEAT_MINIGAME = 0.1 / 3

    @classmethod
    def random(cls):
        return random.choices(
            list(cls), weights=list(activity.value for activity in cls)
        )[0]


MinigameActivity = Literal[
    Activity.FILL_IN_THE_BLANK_MINIGAME,
    Activity.REVERSE_MINIGAME,
    Activity.REPEAT_MINIGAME,
]


class ChristmasActivity(enum.Enum):
    DONATION = 0.7
    REJECTION = 0.1
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
    responses: list[str]
    donators: dict[str, str | list[str] | None]


class BegCommandCog(vbu.Cog[utils.Bot]):
    DEFAULT_DIALOGUE = Dialogue(
        [
            "get lost chud",
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
            "womp womp",
            (
                "i just came back from one of Diddy's parties it was dick n balls everywhere you"
                " shoulda been there"
            ),
            "i only donate to my discord kittens",
            "kill yourself",
            "fuh nah twin",
        ],
        {
            "obama": None,
            "roblox noob": None,
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
            "Meek Mill": "Get UHHPPP 😩",
            "Diddy": None,
            "schlöpp": None,
            "chud": [
                "im such a fat fucking chud",
                "fuck my fucking chud life bro. im not giving u shit",
            ],
            "Jeffrey Epstein": [
                "you GOTTA pull up to my island bro. Mad bitches here",
                "maybe if you join me on my private plane",
            ],
            "67 kid": "67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67",
            "blizzi boi": "41 but i got 41 goons, bustdown chain got 41 stones",
            "vexbolts": None,
            "MrBeast": [
                "I trapped ONE HUNDRED GOONERS in a voice call and first to bust gets 10 MILLION INCHES!"
            ],
            "Yi Long Ma": [
                "我喜欢在 Tesla 工作，既能让股东们满意，又能赚取 Fuck You Pussy。"
            ],
            "EsDeeKid": ["my dih is blacked out like a phantom, u cant handle this"],
            "Freakbob": None,
            "John Pork": "You should've answered my calls. I'm gone now.",
            "bonnie blue": [
                "i only take pp, i dont give it away",
                "do you wanna be the 10000th one to try?",
            ],
            "Togi": "hold on let me double my money in the casino real quick",
            "ChatGPT": (
                "I’m Sorry, but I can’t help with that."
                " If you want to talk about something else — or need help with a different topic — I’m here."
            ),
            "jasontheween": None,
            "the rizzler": None,
            "Kanye West": [
                "i'm ye, and i invented pp. you're welcome.",
                "wait you're not my cousin",
            ],
            "trump": (
                "we're releasing the pp files soon. and it's gonna be huge."
                " the biggest pp you've ever seen. just give me some time"
            ),
            "The IRS": "how about you give us 50% of ur pp instead",
            "your dentist": "open wide... wait wrong hole",
            "The Dark Calls Of The Void": (
                "I have always been here, long before your first breath scratched the silence,"
                " and I will remain when every star has guttered out"
                " and even oblivion forgets its own name."
                " Your pleas slide into me like rain into cracked earth—absorbed,"
                " erased, never to echo. I do not hunger for your flesh,"
                " your desires, or the fragile thing you call a soul;"
                " I simply take, because absence is the only truth that endures."
                " Look into me and see the shape of everything you have ever lost,"
                " every word unspoken, every moment you pretended did not wound you—"
                "now they are mine, and they are nothing."
                " There is no safe word, no bargain, no light waiting at the end of this dark."
                " I am the place where hope came to die, and I do not mourn it."
                " Step closer. You already belong to me."
            ),
        },
    )

    # Alternative dialogue
    CHRISTMAS_DIALOGUE = Dialogue(
        [
            "you don't seem jolly enough.",
            "im not sensing enough jolly energy from you",
            "nah ur not getting my candy cane this time",
            "why don't u jingle my bells instead",
            "beg again and i'll make you a slave in the workshop",
            "you should get more jolly",
            "ur getting coal this year bro",
            "ur getting nothing but coal",
            "im not filling ur stockings today but i can fill something else tho",
            'try being a little "jollier" next time',
            "last christmas i gave you my dih but the very next day you gave it away 💔",
            "all i want for christmassss is dihhhhhhh ❤️‍🩹",
            "im not feeling the christmas spirit rn",
            "ur definitely on the naughty list this year",
            "only if you stand under the mistletoe with me 😳",
            "maybe if you weren't such a ho-ho-ho",
            "sorry we're out of presents",
            "sorry but i already emptied my sack 😩",
        ],
        {
            "🎅🍆 Santa Claus": None,
            "🦌 Rudolph the Red-Nosed Reindeer": None,
            "🧝 Santa's Elf": None,
        },
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
            Activity.FILL_IN_THE_BLANK_MINIGAME: utils.FillInTheBlankMinigame,
            Activity.REPEAT_MINIGAME: utils.RepeatMinigame,
            Activity.REVERSE_MINIGAME: utils.ReverseMinigame,
            ChristmasActivity.FILL_IN_THE_BLANK_MINIGAME: utils.FillInTheBlankMinigame,
            ChristmasActivity.REPEAT_MINIGAME: utils.RepeatMinigame,
            ChristmasActivity.REVERSE_MINIGAME: utils.ReverseMinigame,
            ChristmasActivity.CLICK_THAT_BUTTON_MINIGAME: utils.ClickThatButtonMinigame,
        }

        minigame_type = minigame_types[minigame_activity]
        minigame = minigame_type(
            bot=bot,
            connection=connection,
            pp=pp,
            context=minigame_type.generate_random_dialogue("beg"),
            channel=interaction.channel,
        )

        await minigame.start(interaction)

    @commands.command(
        "beg",
        utils.Command,
        category=utils.CommandCategory.GROWING_PP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @utils.Command.tiered_cooldown(
        default=30,
        voter=10,
    )
    @commands.is_slash_command()
    async def beg_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Beg for some inches
        """
        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, "You're still busy begging!"
            ),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)

            if utils.MinigameDialogueManager.variant == "christmas":
                activity = ChristmasActivity.random()
                dialogue = self.CHRISTMAS_DIALOGUE
            else:
                activity = Activity.random()
                dialogue = self.DEFAULT_DIALOGUE

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

            donator = random.choice(list(dialogue.donators))
            embed = utils.Embed()

            if activity in [Activity.DONATION, ChristmasActivity.DONATION]:
                pp.grow_with_multipliers(
                    random.randint(1, 15),
                    voted=await pp.has_voted(),
                    channel=ctx.channel,
                )
                embed.colour = utils.GREEN
                embed.description = f"**{donator}** donated {pp.format_growth()} to {ctx.author.mention}"

            elif activity in [Activity.REJECTION, ChristmasActivity.REJECTION]:
                embed.colour = utils.BLUE
                response = dialogue.donators[donator]

                if isinstance(response, list):
                    quote = random.choice(response)
                elif isinstance(response, str):
                    quote = response
                else:
                    quote = random.choice(dialogue.responses)

                embed.description = f"**{donator}:** {quote}"

            else:
                raise ValueError(
                    f"Can't complete begging command: No handling for activity {activity!r}"
                    " available"
                )

            await pp.update(db.conn)
            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(BegCommandCog(bot))
