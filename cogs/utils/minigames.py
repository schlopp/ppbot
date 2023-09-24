import asyncio
import itertools
import os
import logging
import random
import uuid
from string import ascii_letters, digits
from typing import Generic, TypeVar, TypedDict, cast

import asyncpg
import discord
import toml

from . import (
    Object,
    Pp,
    Embed,
    InventoryItem,
    ReplyManager,
    ItemManager,
    format_time,
    format_iterable,
    format_slash_command,
    limit_text,
    clean,
    RED,
    PINK,
    MEME_URL,
)

_MinigameContextDictT = TypeVar("_MinigameContextDictT", bound=TypedDict)


class Minigame(Generic[_MinigameContextDictT], Object):
    MAXIMUM_ITEM_REWARD_PRICE = 45
    ID: str

    def __init__(
        self,
        connection: asyncpg.Connection,
        pp: Pp,
        context: _MinigameContextDictT,
    ) -> None:
        self.connection = connection
        self.pp = pp
        self._id = uuid.uuid4().hex
        self.context = context

    @classmethod
    def generate_random_dialogue(cls, section: str = "global") -> _MinigameContextDictT:
        return MinigameDialogueManager.generate_random_dialogue(cls, section)

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
                reward_item = InventoryItem(
                    self.pp.user_id,
                    random.choice(
                        [
                            item_id
                            for item_id, item in itertools.chain(
                                ItemManager.tools.items(),
                                ItemManager.useless.items(),
                                ItemManager.buffs.items(),
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

        return f"{format_iterable(reward_messages, inline=True)}"

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
    ID = "REVERSE"

    async def start(self, interaction: discord.Interaction) -> None:
        embed = Embed()
        embed.colour = PINK
        embed.title = "MINIGAME - REVERSE"

        embed.description = (
            f"{self.context['situation']}"
            f" **Use {format_slash_command('reply')} and enter the phrase in reverse to {self.context['reason']}!**"
            f" \n\n**{self.context['person']}:** {self.context['phrase']}"
        )

        await interaction.response.send_message(embed=embed)

        embed = Embed()
        embed.title = "MINIGAME - REVERSE"

        try:
            assert isinstance(interaction.channel, discord.TextChannel)
            reply_context, reply = await ReplyManager.wait_for_reply(
                interaction.channel
            )
        except asyncio.TimeoutError:
            embed.colour = RED
            embed.description = (
                f"**You're slow as fuck!**  Next time, use **{format_slash_command('reply')}** within"
                f" {format_time(ReplyManager.DEFAULT_TIMEOUT)}."
                f" {self.context['fail']} You win **nothing.**"
            )
            embed.add_tip()
            await interaction.edit_original_message(embed=embed)
            return

        reverse_phrase = "".join(reversed(self.context["phrase"]))

        if self.clean_sentence(reply) != self.clean_sentence(reverse_phrase):
            embed.colour = RED
            embed.description = (
                f"**WRONG!!!!** You fucking loser."
                f" The correct answer was `{reverse_phrase}`. You can't do anything right!"
                f" {self.context['fail']} You win **nothing.**"
            )
        else:
            embed.colour = PINK
            reward = await self.give_random_reward()

            if "{}" in self.context["win"]:
                win_dialogue = self.context["win"].format(reward)
            else:
                win_dialogue = f"{self.context['win']} You win {reward}"

            embed.description = f"**GGS!** {win_dialogue}"

        embed.add_tip()
        await reply_context.interaction.response.send_message(
            limit_text(
                f"**{clean(reply_context.author.display_name)}:** {reply}",
                256,
            ),
            embed=embed,
        )


class RepeatMinigame(Minigame[RepeatContextDict]):
    ID = "REPEAT"

    async def start(self, interaction: discord.Interaction) -> None:
        embed = Embed()
        embed.colour = PINK
        embed.title = "MINIGAME - REPEAT"

        zero_width_character = "​"
        obscured_sentence = zero_width_character.join(self.context["sentence"])

        embed.description = (
            f"{self.context['situation']}"
            f" **Use {format_slash_command('reply')} and enter the sentence to {self.context['reason']}!**"
            f" \n\n**{self.context['person']}:** `{obscured_sentence}`"
        )

        await interaction.response.send_message(embed=embed)

        embed = Embed()
        embed.title = "MINIGAME - REPEAT"

        try:
            assert isinstance(interaction.channel, discord.TextChannel)
            reply_context, reply = await ReplyManager.wait_for_reply(
                interaction.channel
            )
        except asyncio.TimeoutError:
            embed.colour = RED
            embed.description = (
                f"**You're slow as fuck!**  Next time, use {format_slash_command('reply')} within"
                f" {format_time(ReplyManager.DEFAULT_TIMEOUT)}."
                f" {self.context['fail']} You win **nothing.**"
            )
            embed.add_tip()
            await interaction.edit_original_message(embed=embed)
            return

        if zero_width_character in reply:
            embed.colour = RED
            embed.description = (
                "Did you really think I wouldn't notice you copy-pasting the sentence?"
                f" I know everything about you. {self.context['fail']}"
                " You win **nothing.**"
            )
        elif self.clean_sentence(reply) != self.clean_sentence(
            self.context["sentence"]
        ):
            embed.colour = RED
            embed.description = (
                f"**WRONG!!!!** You fucking loser."
                f" The correct answer was `{self.context['sentence']}`. You can't do anything right!"
                f" {self.context['fail']} You win **nothing.**"
            )
        else:
            embed.colour = PINK
            reward = await self.give_random_reward()

            if "{}" in self.context["win"]:
                win_dialogue = self.context["win"].format(reward)
            else:
                win_dialogue = f"{self.context['win']} You win {reward}"

            embed.description = f"**GGS!** {win_dialogue}"

        embed.add_tip()
        await reply_context.interaction.response.send_message(
            limit_text(
                f"**{clean(reply_context.author.display_name)}:** {reply}",
                256,
            ),
            embed=embed,
        )


class FillInTheBlankMinigame(Minigame[FillInTheBlankContextDict]):
    ID = "FILL_IN_THE_BLANK"

    async def start(self, interaction: discord.Interaction) -> None:
        embed = Embed()
        embed.colour = PINK
        embed.title = "MINIGAME - FILL IN THE BLANK"

        # This looks cursed as fuck
        # Should output something along the lines of "`Go `[`fuck`](...)` yourself!`"
        prompt = (
            "`"
            + self.context["prompt"].format(
                " ".join(
                    f"`[`{' '.join(['_'] * len(word))}`]({MEME_URL})`"
                    for word in self.context["answer"].split()
                )
            )
            + "`"
        )
        embed.description = (
            f"{self.context['situation']}"
            f" **Use {format_slash_command('reply')} and fill in the blank to {self.context['reason']}!**"
            f" \n\n**{self.context['person']}:** {prompt}"
        )

        await interaction.response.send_message(embed=embed)

        assert isinstance(interaction.channel, discord.TextChannel)

        embed = Embed()
        embed.title = "MINIGAME - FILL IN THE BLANK"

        try:
            reply_context, reply = await ReplyManager.wait_for_reply(
                interaction.channel
            )
        except asyncio.TimeoutError:
            embed.colour = RED
            embed.description = (
                f"**You're slow as fuck!**  Next time, use {format_slash_command('reply')} within"
                f" {format_time(ReplyManager.DEFAULT_TIMEOUT)}."
                f" {self.context['fail']} You win **nothing.**"
            )
            embed.add_tip()
            await interaction.edit_original_message(embed=embed)
            return

        if self.clean_sentence(reply) != self.clean_sentence(self.context["answer"]):
            embed.colour = RED
            embed.description = (
                f"**WRONG!!!!** You fucking loser."
                f" The correct answer was `{self.context['answer']}`. You can't do anything right!"
                f" {self.context['fail']} You win **nothing.**"
            )
        else:
            embed.colour = PINK
            reward = await self.give_random_reward()

            if "{}" in self.context["win"]:
                win_dialogue = self.context["win"].format(reward)
            else:
                win_dialogue = f"{self.context['win']} You win {reward}"

            embed.description = f"**GGS!** {win_dialogue}"

        embed.add_tip()
        await reply_context.interaction.response.send_message(
            limit_text(
                f"**{clean(reply_context.author.display_name)}:** {reply}",
                256,
            ),
            embed=embed,
        )


class MinigameDialogueManager:
    DIALOGUE_DIRECTORY = "config/minigames"
    dialogue: dict[str, dict[str, list[dict]]] = {}
    _logger = logging.getLogger("vbu.bot.cog.utils.MinigameDialogueManager")

    @classmethod
    def load(cls) -> None:
        cls.dialogue.clear()
        for subpath in os.listdir(cls.DIALOGUE_DIRECTORY):
            assert subpath.endswith(".toml"), (
                f"Loading minigame dialogue failed: Dialogue directory {cls.DIALOGUE_DIRECTORY!r}"
                " contains non-TOML files."
            )
            cls.dialogue.update(
                {
                    subpath.rsplit(".")[0]: toml.load(
                        f"{cls.DIALOGUE_DIRECTORY}/{subpath}"
                    )
                }
            )
            cls._logger.info(
                f" * Added dialogue from {cls.DIALOGUE_DIRECTORY}/{subpath}"
            )

    @classmethod
    def generate_random_dialogue(
        cls,
        minigame_type: type[Minigame[_MinigameContextDictT]],
        section: str = "global",
    ) -> _MinigameContextDictT:
        section_dialogue = cls.dialogue.get(section, {})
        dialogue_options = section_dialogue.get(minigame_type.ID, [])

        if not dialogue_options:
            raise ValueError(
                "No minigame dialogue options associated with the"
                f" section {section!r} found in config/minigames.toml"
            )

        dialogue_option = random.choice(dialogue_options)
        try:
            if minigame_type == FillInTheBlankMinigame:
                prompt, answer = random.choice(dialogue_option["prompts"])
                fill_in_the_blank_dialogue: FillInTheBlankContextDict = {
                    "person": dialogue_option["person"],
                    "situation": random.choice(dialogue_option["situations"]),
                    "reason": random.choice(dialogue_option["reasons"]),
                    "prompt": prompt,
                    "answer": answer,
                    "fail": random.choice(dialogue_option["fails"]),
                    "win": random.choice(dialogue_option["wins"]),
                }

                return cast(_MinigameContextDictT, fill_in_the_blank_dialogue)

            elif minigame_type == ReverseMinigame:
                reverse_dialogue: ReverseContextDict = {
                    "person": dialogue_option["person"],
                    "situation": random.choice(dialogue_option["situations"]),
                    "reason": random.choice(dialogue_option["reasons"]),
                    "phrase": random.choice(dialogue_option["phrases"]),
                    "fail": random.choice(dialogue_option["fails"]),
                    "win": random.choice(dialogue_option["wins"]),
                }
                return cast(_MinigameContextDictT, reverse_dialogue)

            elif minigame_type == RepeatMinigame:
                repeat_dialogue: RepeatContextDict = {
                    "person": dialogue_option["person"],
                    "situation": random.choice(dialogue_option["situations"]),
                    "reason": random.choice(dialogue_option["reasons"]),
                    "sentence": random.choice(dialogue_option["sentences"]),
                    "fail": random.choice(dialogue_option["fails"]),
                    "win": random.choice(dialogue_option["wins"]),
                }
                return cast(_MinigameContextDictT, repeat_dialogue)
        except KeyError as exc:
            raise ValueError(
                f"Can't generate minigame dialogue: Element of section {section!r}, minigame"
                f" {minigame_type.ID!r} missing required key {exc.args[0]!r}"
            )
        except IndexError as exc:
            raise ValueError(
                f"Can't generate minigame dialogue: Element of section {section!r}, minigame"
                f" {minigame_type.ID!r} contains empty dialogue array"
            )

        raise ValueError(
            f"Can't generate minigame dialogue: No handling for minigame {minigame_type!r} available"
        )
