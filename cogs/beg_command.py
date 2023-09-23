import asyncio
import enum
import itertools
import random
import uuid
from typing import TypedDict, Literal, Generic, TypeVar, cast
from string import ascii_letters, digits

import asyncpg
import discord
import toml
from discord.ext import commands, vbu

from cogs.utils.bot import Bot

from . import utils


_MinigameContextDictT = TypeVar("_MinigameContextDictT", bound=TypedDict)


class Activity(enum.Enum):
    DONATION = 0.7
    REJECTION = 0.1
    FILL_IN_THE_BLANK_MINIGAME = 0.2 / 3
    REVERSE_MINIGAME = 0.2 / 3
    REPEAT_MINIGAME = 0.2 / 3

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


class Minigame(Generic[_MinigameContextDictT], utils.Object):
    MAXIMUM_ITEM_REWARD_PRICE = 45

    def __init__(
        self,
        connection: asyncpg.Connection,
        pp: utils.Pp,
        context: _MinigameContextDictT,
    ) -> None:
        self.connection = connection
        self.pp = pp
        self._id = uuid.uuid4().hex
        self.context = context

    async def give_random_reward(self) -> str:
        reward_messages: list[str] = []

        self.pp.grow(random.randint(30, 60))
        await self.pp.update(self.connection)
        reward_messages.append(self.pp.format_growth())

        reward_item_ids: list[str] = []
        while True:
            # 50% 1 item, ~33% 2 items, ~12.5% 3 items, ~4% 4 or more items
            if reward_item_ids and random.randint(0, len(reward_item_ids)):
                break
            try:
                reward_item = utils.InventoryItem(
                    self.pp.user_id,
                    random.choice(
                        [
                            item_id
                            for item_id, item in itertools.chain(
                                utils.ItemManager.tools.items(),
                                utils.ItemManager.useless.items(),
                                utils.ItemManager.buffs.items(),
                            )
                            if item.price
                            < self.MAXIMUM_ITEM_REWARD_PRICE * self.pp.multiplier.value
                        ]
                    ),
                    0,
                )
            except IndexError:
                break
            else:
                if reward_item.id in reward_item_ids:
                    break
                reward_item.amount.value += random.randint(
                    1,
                    self.MAXIMUM_ITEM_REWARD_PRICE
                    * self.pp.multiplier.value
                    // reward_item.item.price
                    * 3,
                )
                await reward_item.update(self.connection, additional=True)
                reward_item_ids.append(reward_item.id)
                reward_messages.append(
                    f"{reward_item.format_item()} ({reward_item.item.category.lower()})"
                )

        return f"{utils.format_iterable(reward_messages, inline=True)}"

    @staticmethod
    def clean_sentence(sentence: str):
        return "".join(
            character
            for character in sentence.lower()
            if character in ascii_letters + digits
        )

    async def start(self, interaction: discord.Interaction) -> None:
        raise NotImplementedError


class FillInTheBlankContextDict(TypedDict):
    person: str
    situation: str
    reason: str
    prompt: str
    answer: str
    fail: str
    win: str


class ReverseContextDict(TypedDict):
    person: str
    situation: str
    reason: str
    phrase: str
    fail: str
    win: str


class RepeatContextDict(TypedDict):
    person: str
    situation: str
    reason: str
    sentence: str
    fail: str
    win: str


class ReverseMinigame(Minigame[ReverseContextDict]):
    async def start(self, interaction: discord.Interaction) -> None:
        embed = utils.Embed()
        embed.colour = utils.PINK
        embed.title = "MINIGAME - REVERSE"

        embed.description = (
            f"{self.context['situation']}"
            f" **Use /reply and enter the phrase in reverse to {self.context['reason']}!**"
            f" \n\n**{self.context['person']}:** {self.context['phrase']}"
        )

        embed.set_footer(
            text=(
                "use /reply to respond to this minigame!"
                " - not case sensitive, only letters and numbers are looked at"
            )
        )

        await interaction.response.send_message(embed=embed)

        embed = utils.Embed()
        embed.title = "MINIGAME - REVERSE"

        try:
            assert isinstance(interaction.channel, discord.TextChannel)
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

        reverse_phrase = "".join(reversed(self.context["phrase"]))

        if self.clean_sentence(reply) != self.clean_sentence(reverse_phrase):
            embed.colour = utils.RED
            embed.description = (
                f"**WRONG!!!!** You fucking loser."
                f" The correct answer was `{reverse_phrase}`. You can't do anything right!"
                f" {self.context['fail']} You win **nothing.**"
            )
        else:
            embed.colour = utils.GREEN
            reward = await self.give_random_reward()

            if "{}" in self.context["win"]:
                win_dialogue = self.context["win"].format(reward)
            else:
                win_dialogue = f"{self.context['win']} You win {reward}"

            embed.description = f"**GGS!** {win_dialogue}"

        embed.add_tip()
        await reply_context.interaction.response.send_message(
            utils.limit_text(
                f"**{utils.clean(reply_context.author.display_name)}:** {reply}",
                256,
            ),
            embed=embed,
        )


class RepeatMinigame(Minigame[RepeatContextDict]):
    async def start(self, interaction: discord.Interaction) -> None:
        embed = utils.Embed()
        embed.colour = utils.PINK
        embed.title = "MINIGAME - REPEAT"

        zero_width_character = "​"
        obscured_sentence = zero_width_character.join(self.context["sentence"])

        embed.description = (
            f"{self.context['situation']}"
            f" **Use /reply and enter the sentence to {self.context['reason']}!**"
            f" \n\n**{self.context['person']}:** `{obscured_sentence}`"
        )

        embed.set_footer(
            text=(
                "use /reply to respond to this minigame!"
                " - not case sensitive, only letters and numbers are looked at"
            )
        )

        await interaction.response.send_message(embed=embed)

        embed = utils.Embed()
        embed.title = "MINIGAME - REPEAT"

        try:
            assert isinstance(interaction.channel, discord.TextChannel)
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

        if zero_width_character in reply:
            embed.colour = utils.RED
            embed.description = (
                "Did you really think I wouldn't notice you copy-pasting the sentence?"
                f" I know everything about you. {self.context['fail']}"
                " You win **nothing.**"
            )
        elif self.clean_sentence(reply) != self.clean_sentence(
            self.context["sentence"]
        ):
            embed.colour = utils.RED
            embed.description = (
                f"**WRONG!!!!** You fucking loser."
                f" The correct answer was `{self.context['sentence']}`. You can't do anything right!"
                f" {self.context['fail']} You win **nothing.**"
            )
        else:
            embed.colour = utils.GREEN
            reward = await self.give_random_reward()

            if "{}" in self.context["win"]:
                win_dialogue = self.context["win"].format(reward)
            else:
                win_dialogue = f"{self.context['win']} You win {reward}"

            embed.description = f"**GGS!** {win_dialogue}"

        embed.add_tip()
        await reply_context.interaction.response.send_message(
            utils.limit_text(
                f"**{utils.clean(reply_context.author.display_name)}:** {reply}",
                256,
            ),
            embed=embed,
        )


class FillInTheBlankMinigame(Minigame):
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
            f" **Use /reply and fill in the blank to {self.context['reason']}!**"
            f" \n\n**{self.context['person']}:** {prompt}"
        )

        embed.set_footer(
            text=(
                "use /reply to respond to this minigame!"
                " - not case sensitive, only letters and numbers are looked at"
            )
        )

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

        if self.clean_sentence(reply) != self.clean_sentence(self.context["answer"]):
            embed.colour = utils.RED
            embed.description = (
                f"**WRONG!!!!** You fucking loser."
                f" The correct answer was `{self.context['answer']}`. You can't do anything right!"
                f" {self.context['fail']} You win **nothing.**"
            )
        else:
            embed.colour = utils.GREEN
            reward = await self.give_random_reward()

            if "{}" in self.context["win"]:
                win_dialogue = self.context["win"].format(reward)
            else:
                win_dialogue = f"{self.context['win']} You win {reward}"

            embed.description = f"**GGS!** {win_dialogue}"

        embed.add_tip()
        await reply_context.interaction.response.send_message(
            utils.limit_text(
                f"**{utils.clean(reply_context.author.display_name)}:** {reply}",
                256,
            ),
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
        minigame_activity: MinigameActivity,
        *,
        connection: asyncpg.Connection,
        pp: utils.Pp,
        interaction: discord.Interaction,
    ):
        minigame_category = minigame_activity.name.rsplit("_", 1)[0]
        minigame_dialogue: dict = random.choice(
            self.minigame_config.get(minigame_category, [])
            + self.minigame_config.get("beg", {}).get(minigame_category, [])
        )

        if minigame_activity == Activity.FILL_IN_THE_BLANK_MINIGAME:
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
                    "win": random.choice(minigame_dialogue["wins"]),
                },
            )
        elif minigame_activity == Activity.REVERSE_MINIGAME:
            minigame = ReverseMinigame(
                connection,
                pp,
                {
                    "person": minigame_dialogue["person"],
                    "situation": random.choice(minigame_dialogue["situations"]),
                    "reason": random.choice(minigame_dialogue["reasons"]),
                    "phrase": random.choice(minigame_dialogue["phrases"]),
                    "fail": random.choice(minigame_dialogue["fails"]),
                    "win": random.choice(minigame_dialogue["wins"]),
                },
            )
        else:
            minigame = RepeatMinigame(
                connection,
                pp,
                {
                    "person": minigame_dialogue["person"],
                    "situation": random.choice(minigame_dialogue["situations"]),
                    "reason": random.choice(minigame_dialogue["reasons"]),
                    "sentence": random.choice(minigame_dialogue["sentences"]),
                    "fail": random.choice(minigame_dialogue["fails"]),
                    "win": random.choice(minigame_dialogue["wins"]),
                },
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
