import asyncio
import enum
import itertools
import random
import uuid
from typing import TypedDict, Literal

import asyncpg
import discord
import toml
from discord.ext import commands, vbu

from cogs.utils.bot import Bot

from . import utils


class Activity(enum.Enum):
    DONATION = 0.8
    REJECTION = 0.15
    FILL_IN_THE_BLANK_MINIGAME = .05

    @classmethod
    def random(cls):
        return random.choices(
            list(Activity), weights=list(activity.value for activity in Activity)
        )[0]


class Minigame(utils.Object):
    MAXIMUM_ITEM_REWARD_PRICE = 50

    def __init__(self, connection: asyncpg.Connection, pp: utils.Pp) -> None:
        self.connection = connection
        self.pp = pp
        self._id = uuid.uuid4().hex

    async def give_random_reward(self) -> str:
        reward_messages: list[str] = []

        self.pp.grow(random.randint(40, 80))
        await self.pp.update(self.connection)
        reward_messages.append(self.pp.format_growth())

        try:
            reward_item = utils.InventoryItem(
                self.pp.user_id,
                random.choice(
                    [
                        item_id
                        for item_id, item in itertools.chain(
                            utils.ItemManager.tools.items(),
                            utils.ItemManager.useless.items(),
                        )
                        if item.price
                        < self.MAXIMUM_ITEM_REWARD_PRICE * self.pp.multiplier.value
                    ]
                ),
                0,
            )
        except IndexError:
            pass
        else:
            reward_item.amount.value += random.randint(
                1,
                self.MAXIMUM_ITEM_REWARD_PRICE
                * self.pp.multiplier.value
                // reward_item.item.price
                * 3,
            )
            await reward_item.update(self.connection, additional=True)
            reward_messages.append(
                f"{reward_item.format_item()} ({reward_item.item.category.lower()})"
            )

        return f"{utils.format_iterable(reward_messages, inline=True)}"

    async def start(self, interaction: discord.Interaction) -> None:
        raise NotImplementedError


class FillInTheBlankContextDict(TypedDict):
    person: str
    situation: str
    reason: str
    prompt: str
    answer: str
    fail: str


class FillInTheBlankMinigame(Minigame):
    """
    Format:
    {situation} **Use /reply to fill in the blank and {reason}!**

    **{person}:** \\`{prompt with answer}\\`

    Failure format:
    **WRONG!!!!** You fucking loser. You can't do anything right! {fail}
    """

    def __init__(
        self,
        connection: asyncpg.Connection,
        pp: utils.Pp,
        context: FillInTheBlankContextDict,
    ) -> None:
        super().__init__(connection, pp)
        self.context = context

    async def start(self, interaction: discord.Interaction) -> None:
        embed = utils.Embed()
        embed.colour = utils.PINK
        embed.title = "MINIGAME - FILL IN THE BLANK"

        # This looks cursed as fuck
        # Should output something along the lines of "`Go `[`fuck`](...)` yourself!`"
        prompt = (
            "`"
            + self.context["prompt"].format(
                " ".join(
                    f"`[`{' '.join(['_'] * len(word))}`]({utils.MEME_URL})`"
                    for word in self.context["answer"].split()
                )
            )
            + "`"
        )
        embed.description = (
            f"{self.context['situation']}"
            f" **Use /reply to fill in the blank and {self.context['reason']}!**"
            f" \n\n**{self.context['person']}:** {prompt}"
        )

        embed.set_footer(text="use /reply to respond to this minigame!")

        await interaction.response.send_message(embed=embed)

        assert isinstance(interaction.channel, discord.TextChannel)

        embed = utils.Embed()
        embed.title = "MINIGAME - FILL IN THE BLANK"

        try:
            reply_context, reply = await utils.ReplyManager.wait_for_reply(
                interaction.channel
            )
        except asyncio.TimeoutError:
            embed.colour = utils.RED
            embed.description = (
                "**You're slow as fuck!**  Next time, use **/reply** within"
                f" {utils.format_time(utils.ReplyManager.DEFAULT_TIMEOUT)}."
                f" {self.context['fail']} You win **nothing.**"
            )
            embed.add_tip()
            await interaction.edit_original_message(embed=embed)
            return

        if reply != self.context["answer"]:
            embed.colour = utils.RED
            embed.description = (
                f"**WRONG!!!!** You fucking loser."
                f" The correct answer was `{self.context['answer']}`. You can't do anything right!"
                f" {self.context['fail']} You win **nothing.**"
            )
        else:
            embed.colour = utils.GREEN
            embed.description = f"**GGS!** you win {await self.give_random_reward()}"

        embed.add_tip()
        await reply_context.interaction.response.send_message(
            f"**{utils.clean(reply_context.author.display_name)}:** {reply}",
            embed=embed,
        )


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
        self.minigame_config = toml.load("config/minigames.toml")

    async def start_minigame(
        self,
        minigame_activity: Literal[Activity.FILL_IN_THE_BLANK_MINIGAME],
        *,
        connection: asyncpg.Connection,
        pp: utils.Pp,
        interaction: discord.Interaction,
    ):
        if minigame_activity == Activity.FILL_IN_THE_BLANK_MINIGAME:
            minigame_dialogue: dict = random.choice(
                self.minigame_config["FILL_IN_THE_BLANK"]
            )

            prompt, answer = random.choice(minigame_dialogue["prompts"])
            minigame = FillInTheBlankMinigame(
                connection,
                pp,
                {
                    "person": minigame_dialogue["person"],
                    "situation": random.choice(minigame_dialogue["situations"]),
                    "reason": random.choice(minigame_dialogue["reasons"]),
                    "prompt": prompt,
                    "answer": answer,
                    "fail": random.choice(minigame_dialogue["fails"]),
                },
            )
            await minigame.start(interaction)
            return

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

        async with utils.DatabaseWrapper() as db, db.conn.transaction():
            try:
                pp = await utils.Pp.fetch(
                    db.conn,
                    {"user_id": ctx.author.id},
                    lock=utils.RowLevelLockMode.FOR_UPDATE,
                )
            except utils.RecordNotFoundError:
                raise commands.CheckFailure("You don't have a pp!")

            activity = Activity.random()

            if activity in (activity.FILL_IN_THE_BLANK_MINIGAME,):
                await self.start_minigame(
                    activity, connection=db.conn, pp=pp, interaction=ctx.interaction
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
            else:
                embed.colour = utils.BLUE
                response = self.DONATORS[donator]

                if isinstance(response, list):
                    quote = random.choice(response)
                elif isinstance(response, str):
                    quote = response
                else:
                    quote = random.choice(self.RESPONSES)

                embed.description = f"**{donator}:** {quote}"

            await pp.update(db.conn)
            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)


def setup(bot: utils.Bot):
    bot.add_cog(BegCommandCog(bot))
