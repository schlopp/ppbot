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
    Bot,
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
    wait_for_component_interaction,
)

_MinigameContextDictT = TypeVar("_MinigameContextDictT", bound=TypedDict)


ZERO_WIDTH_CHARACTER = "​"


class Minigame(Generic[_MinigameContextDictT], Object):
    MAXIMUM_ITEM_REWARD_PRICE = 45
    ID: str

    def __init__(
        self,
        *,
        bot: Bot,
        connection: asyncpg.Connection,
        pp: Pp,
        context: _MinigameContextDictT,
    ) -> None:
        self.bot = bot
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
            reward_messages.append(reward_item.format_item())

        return format_iterable(reward_messages, inline=True)

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


class ClickThatButtonContextDict(TypedDict):
    object: str
    action: str
    target: str
    target_emoji: str | None
    fail: str
    win: str
    foreground_style: discord.ui.ButtonStyle
    background_style: discord.ui.ButtonStyle
    background_label: str
    background_emoji: str | None


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
                interaction.channel, check=lambda ctx, _: ctx.author == interaction.user
            )
        except asyncio.TimeoutError:
            embed.colour = RED
            embed.description = (
                f"{interaction.user.mention} **You're slow as fuck!** Next time, use"
                f" {format_slash_command('reply')} within"
                f" {format_time(ReplyManager.DEFAULT_TIMEOUT)}. {self.context['fail']} You win"
                " **nothing.**"
            )
            embed.add_tip()

            try:
                await interaction.edit_original_message(embed=embed)
            except discord.HTTPException:
                try:
                    assert isinstance(interaction.channel, discord.abc.Messageable)
                    await interaction.channel.send(embed=embed)
                except discord.HTTPException:
                    pass

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

            embed.description = f"{interaction.user.mention} **GGS!** {win_dialogue}"

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

        obscured_sentence = ZERO_WIDTH_CHARACTER.join(self.context["sentence"])

        embed.description = (
            f"{interaction.user.mention} {self.context['situation']}"
            f" **Use {format_slash_command('reply')} and enter the sentence to {self.context['reason']}!**"
            f" \n\n**{self.context['person']}:** `{obscured_sentence}`"
        )

        await interaction.response.send_message(embed=embed)

        embed = Embed()
        embed.title = "MINIGAME - REPEAT"

        try:
            assert isinstance(interaction.channel, discord.TextChannel)
            reply_context, reply = await ReplyManager.wait_for_reply(
                interaction.channel, check=lambda ctx, _: ctx.author == interaction.user
            )
        except asyncio.TimeoutError:
            embed.colour = RED
            embed.description = (
                f"{interaction.user.mention} **You're slow as fuck!** Next time, use"
                f" {format_slash_command('reply')} within"
                f" {format_time(ReplyManager.DEFAULT_TIMEOUT)}. {self.context['fail']} You win"
                " **nothing.**"
            )
            embed.add_tip()

            try:
                await interaction.edit_original_message(embed=embed)
            except discord.HTTPException:
                try:
                    assert isinstance(interaction.channel, discord.abc.Messageable)
                    await interaction.channel.send(embed=embed)
                except discord.HTTPException:
                    pass

            return

        if ZERO_WIDTH_CHARACTER in reply:
            embed.colour = RED
            embed.description = (
                f"{interaction.user.mention} Did you really think I wouldn't notice you"
                " copy-pasting the sentence? I know everything about you."
                f" {self.context['fail']} You win **nothing.**"
            )
        elif self.clean_sentence(reply) != self.clean_sentence(
            self.context["sentence"]
        ):
            embed.colour = RED
            embed.description = (
                f"{interaction.user.mention} **WRONG!!!!** You fucking loser."
                f" The correct answer was `{self.context['sentence']}`. You can't do anything"
                f" right! {self.context['fail']} You win **nothing.**"
            )
        else:
            embed.colour = PINK
            reward = await self.give_random_reward()

            if "{}" in self.context["win"]:
                win_dialogue = self.context["win"].format(reward)
            else:
                win_dialogue = f"{self.context['win']} You win {reward}"

            embed.description = f"{interaction.user.mention} **GGS!** {win_dialogue}"

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
            f"{interaction.user.mention} {self.context['situation']}"
            f" **Use {format_slash_command('reply')} and fill in the blank to"
            f" {self.context['reason']}!** \n\n**{self.context['person']}:** {prompt}"
        )

        await interaction.response.send_message(embed=embed)

        assert isinstance(interaction.channel, discord.TextChannel)

        embed = Embed()
        embed.title = "MINIGAME - FILL IN THE BLANK"

        try:
            reply_context, reply = await ReplyManager.wait_for_reply(
                interaction.channel, check=lambda ctx, _: ctx.author == interaction.user
            )
        except asyncio.TimeoutError:
            embed.colour = RED
            embed.description = (
                f"{interaction.user.mention} **You're slow as fuck!** Next time, use"
                f" {format_slash_command('reply')} within"
                f" {format_time(ReplyManager.DEFAULT_TIMEOUT)}. {self.context['fail']} You win"
                " **nothing.**"
            )
            embed.add_tip()

            try:
                await interaction.edit_original_message(embed=embed)
            except discord.HTTPException:
                try:
                    assert isinstance(interaction.channel, discord.abc.Messageable)
                    await interaction.channel.send(embed=embed)
                except discord.HTTPException:
                    pass

            return

        if self.clean_sentence(reply) != self.clean_sentence(self.context["answer"]):
            embed.colour = RED
            embed.description = (
                f"{interaction.user.mention} **WRONG!!!!** You fucking loser."
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

            embed.description = f"{interaction.user.mention} **GGS!** {win_dialogue}"

        embed.add_tip()
        await reply_context.interaction.response.send_message(
            limit_text(
                f"**{clean(reply_context.author.display_name)}:** {reply}",
                256,
            ),
            embed=embed,
        )


class ClickThatButtonMinigame(Minigame[ClickThatButtonContextDict]):
    ID = "CLICK_THAT_BUTTON"
    GRID_HEIGHT = 2
    GRID_WIDTH = 5
    TIMEOUT = 10

    def __init__(
        self,
        *,
        bot: Bot,
        connection: asyncpg.Connection,
        pp: Pp,
        context: ClickThatButtonContextDict,
    ) -> None:
        super().__init__(bot=bot, connection=connection, pp=pp, context=context)

        self._components = discord.ui.MessageComponents(
            *(
                discord.ui.ActionRow(
                    *(
                        discord.ui.Button(
                            label=self.context["background_label"],
                            emoji=self.context["background_emoji"],
                            custom_id=f"{self._id}_{x}_{y}",
                            style=self.context["background_style"],
                        )
                        for x in range(self.GRID_WIDTH)
                    )
                )
                for y in range(self.GRID_HEIGHT)
            )
        )
        self._target_coords_history: list[tuple[int, int]] = []
        self._target_coords: tuple[int, int] | None = None
        self._last_target_coords_index: int | None = None
        self._interaction: discord.Interaction | None = None

    def _replace_button(self, x: int, y: int, button: discord.ui.Button) -> None:
        row = cast(discord.ui.ActionRow, self._components.components[y])
        row.components[x] = button

    def _move_target(self) -> None:
        if self._target_coords is not None:
            x, y = self._target_coords
            self._replace_button(
                x,
                y,
                discord.ui.Button(
                    label=self.context["background_label"],
                    emoji=self.context["background_emoji"],
                    custom_id=f"{self._id}_{x}_{y}",
                    style=self.context["background_style"],
                ),
            )
        else:
            self._last_target_coords_index = 0

        self._target_coords = (
            random.randrange(0, self.GRID_WIDTH),
            random.randrange(0, self.GRID_HEIGHT),
        )
        self._target_coords_history.append(self._target_coords)

        x, y = self._target_coords

        self._replace_button(
            x,
            y,
            discord.ui.Button(
                label=self.context["target"],
                emoji=self.context["target_emoji"],
                custom_id=f"{self._id}_TARGET_{x}_{y}",
                style=self.context["foreground_style"],
            ),
        )

    async def _move_target_loop(self, interaction: discord.Interaction) -> None:
        while True:
            await asyncio.sleep(1 + random.random())
            self._move_target()

            try:
                await interaction.edit_original_message(components=self._components)
            except discord.HTTPException:
                break

            assert self._last_target_coords_index is not None
            self._last_target_coords_index += 1

    def _disable_components(
        self, coords: tuple[int, int] | None = None, *, target: bool = False
    ) -> None:
        assert self._target_coords is not None

        if target:
            assert coords is not None
            target_coords = coords
        elif self._last_target_coords_index is None:
            target_coords = self._target_coords
        else:
            target_coords = self._target_coords_history[self._last_target_coords_index]

        self._components = discord.ui.MessageComponents(
            *(
                discord.ui.ActionRow(
                    *(
                        discord.ui.Button(
                            label=self.context["background_label"],
                            emoji=self.context["background_emoji"],
                            disabled=True,
                        )
                        for _ in range(self.GRID_WIDTH)
                    )
                )
                for _ in range(self.GRID_HEIGHT)
            )
        )

        target_button = discord.ui.Button(
            label=self.context["target"],
            emoji=self.context["target_emoji"],
            style=discord.ButtonStyle.green,
        )
        target_button.style = discord.ButtonStyle.green
        self._replace_button(*target_coords, target_button)

        if not target and coords is not None:
            self._replace_button(
                *coords,
                discord.ui.Button(
                    label=self.context["background_label"],
                    emoji=self.context["background_emoji"],
                    style=discord.ui.ButtonStyle.red,
                ),
            )

        self._components.disable_components()

    async def start(self, interaction: discord.Interaction) -> None:
        embed = Embed()
        embed.colour = PINK
        embed.title = (
            f"MINIGAME - {self.context['action'].upper()} THAT"
            f" {self.context['object'].upper()}"
        )

        self._move_target()

        await interaction.response.send_message(
            embed=embed, components=self._components
        )

        move_target_loop = self.bot.loop.create_task(
            self._move_target_loop(interaction)
        )

        embed = Embed()
        embed.title = (
            f"MINIGAME - {self.context['action'].upper()} THAT"
            f" {self.context['object'].upper()}"
        )

        try:
            _, action = await wait_for_component_interaction(
                self.bot, self._id, users=[interaction.user], timeout=self.TIMEOUT
            )
        except asyncio.TimeoutError:
            move_target_loop.cancel()
            self._disable_components()

            embed.colour = RED
            embed.description = (
                f"{interaction.user.mention} **You're slow as fuck!** Should've clicked the "
                f"{self.context['object']} within {format_time(self.TIMEOUT)}."
                f" {self.context['fail']} You win **nothing.**"
            )
            embed.add_tip()

            try:
                await interaction.edit_original_message(
                    embed=embed, components=self._components
                )
            except discord.HTTPException:
                try:
                    assert isinstance(interaction.channel, discord.abc.Messageable)
                    await interaction.channel.send(
                        embed=embed, components=self._components
                    )
                except discord.HTTPException:
                    pass

            return

        move_target_loop.cancel()

        if not action.startswith("TARGET"):
            x, y = map(int, action.split("_"))
            self._disable_components((x, y))

            embed.colour = RED
            embed.description = (
                f"{interaction.user.mention} **WRONG!!!!** You fucking loser."
                f" Are you blind or something? Just click the {self.context['object']}"
                f", it's not that hard bro. {self.context['fail']} You win **nothing.**"
            )
        else:
            x, y = map(int, action.split("_")[1:])
            self._disable_components((x, y), target=True)
            embed.colour = PINK
            reward = await self.give_random_reward()

            if "{}" in self.context["win"]:
                win_dialogue = self.context["win"].format(reward)
            else:
                win_dialogue = f"{self.context['win']} You win {reward}"

            embed.description = f"{interaction.user.mention} **GGS!** {win_dialogue}"

        embed.add_tip()

        try:
            await interaction.delete_original_message()
        except discord.HTTPException:
            pass

        assert isinstance(interaction.channel, discord.abc.Messageable)

        try:
            await interaction.channel.send(embed=embed, components=self._components)
        except discord.HTTPException:
            pass


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

            elif minigame_type == ClickThatButtonMinigame:
                click_that_button_dialogue: ClickThatButtonContextDict = {
                    "object": dialogue_option["object"],
                    "action": dialogue_option.get("action", "click"),
                    "target": dialogue_option.get("target", ZERO_WIDTH_CHARACTER),
                    "target_emoji": dialogue_option.get("target_emoji"),
                    "fail": random.choice(dialogue_option["fails"]),
                    "win": random.choice(dialogue_option["wins"]),
                    "foreground_style": getattr(
                        discord.ButtonStyle,
                        dialogue_option.get("foreground_style", "green"),
                    ),
                    "background_style": getattr(
                        discord.ButtonStyle,
                        dialogue_option.get("background_style", "grey"),
                    ),
                    "background_label": dialogue_option.get(
                        "background_label", ZERO_WIDTH_CHARACTER
                    ),
                    "background_emoji": dialogue_option.get("background_emoji"),
                }

                if (
                    click_that_button_dialogue["target"] == ZERO_WIDTH_CHARACTER
                    and click_that_button_dialogue["target_emoji"] is None
                ):
                    raise ValueError(
                        f"Can't generate minigame dialogue: Element of section {section!r}"
                        f", minigame {minigame_type.ID!r} missing required key {'target'!r}, which"
                        f" is only optional when key {'target_emoji'} is supplied"
                    )

                return cast(_MinigameContextDictT, click_that_button_dialogue)

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
        except AttributeError as exc:
            if (
                exc.obj != discord.ButtonStyle
            ):  # pyright: ignore  # exc.obj isn't always object
                raise
            raise ValueError(
                f"Can't generate minigame dialogue: Style element of section {section!r}, minigame"
                f" {minigame_type.ID!r} contains invalid ButtonStyle {exc.name!r}"
            )

        raise ValueError(
            f"Can't generate minigame dialogue: No handling for minigame {minigame_type!r}"
            " available"
        )
