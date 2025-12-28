import asyncio
import enum
import uuid
import random
from datetime import datetime, timedelta, UTC
from typing import Self, Literal, NoReturn

import discord
from discord.ext import commands, vbu, tasks

from . import utils


class InvalidAction(Exception):
    pass


class ExternalLeave(Exception):
    pass


class CasinoState(enum.Enum):
    MENU = enum.auto()
    CHANGING_STAKES = enum.auto()
    PLAYING_DICE = enum.auto()
    PLAYING_BLACKJACK = enum.auto()


class CasinoStakes(enum.Enum):
    MAX = enum.auto()


class CasinoSession(utils.Object):
    TIMEOUT = 30
    MIN_STAKES = 25
    MAX_STAKES = 10**7
    cache: dict[commands.SlashContext[utils.Bot], Self] = {}
    _repr_attributes = ("ctx", "id", "stakes", "pp", "state")

    def __init__(self, ctx: commands.SlashContext[utils.Bot], pp: utils.Pp) -> None:
        self.ctx = ctx
        self.id = uuid.uuid4().hex
        self._stakes = max(min(pp.size.value, self.MAX_STAKES, 1000), self.MIN_STAKES)
        self.pp = pp
        self.game_embed = utils.Embed()
        self.game_embed.set_author(
            name=f"{utils.clean(self.ctx.author.display_name).title()}'s Casino"
        )
        self.game_components = discord.ui.MessageComponents()
        self.state = CasinoState.MENU
        self.last_interaction: datetime | None = datetime.now(UTC).replace(tzinfo=None)
        self.cache[ctx] = self

    @property
    def stakes(self) -> int:
        if self._stakes == CasinoStakes.MAX:
            return max(min(self.pp.size.value, self.MAX_STAKES), self.MIN_STAKES)
        return self._stakes

    def generate_stat_description(self, *, note_invalid_stakes: bool = False) -> str:
        description = utils.format_iterable(
            [
                f"During this session, you've {self.pp.format_growth(prefixed=True)}",
                f"Your pp now has {self.pp.format_growth(self.pp.size.value)}",
            ]
        )

        if not note_invalid_stakes:
            return description

        if self.pp.size.value < self.MIN_STAKES:
            description += (
                "\n\n**IMPORTANT:** You can't afford to gamble! The minimum stakes are"
                f" {self.pp.format_growth(self.MIN_STAKES)}. Please leave the casino."
            )
        elif self.pp.size.value < self.stakes:
            description += (
                "\n\n**IMPORTANT:** Your stakes are too high! Please change them"
                ", or leave the casino."
            )

        return description

    def generate_menu_components(self) -> discord.ui.MessageComponents:
        stakes_label = f"Stakes: {self.pp.format_growth(self.stakes, markdown=None)}"
        if self.pp.size.value < self.stakes:
            stakes_label += " (You can't afford that!)"
        elif self._stakes is CasinoStakes.MAX:
            stakes_label += " (max)"
        return discord.ui.MessageComponents(
            discord.ui.ActionRow(
                discord.ui.Button(
                    label="Dice",
                    custom_id=f"{self.id}_DICE",
                    style=discord.ButtonStyle.green,
                    emoji="🎲",
                    disabled=self.pp.size.value < self.stakes,
                ),
                discord.ui.Button(
                    label="Blackjack",
                    custom_id=f"{self.id}_BLACKJACK",
                    style=discord.ButtonStyle.green,
                    emoji="🃏",
                    disabled=self.pp.size.value < self.stakes,
                ),
                discord.ui.Button(
                    label="Deathroll (SOON!)",
                    custom_id=f"{self.id}_DEATHROLL",
                    style=discord.ButtonStyle.green,
                    emoji="🪦",
                    disabled=True,
                ),
            ),
            discord.ui.ActionRow(
                discord.ui.Button(
                    label=stakes_label,
                    custom_id=f"{self.id}_STAKES",
                    disabled=self.pp.size.value < self.MIN_STAKES,
                ),
                discord.ui.Button(
                    label=f"Leave",
                    custom_id=f"{self.id}_LEAVE",
                    style=discord.ButtonStyle.red,
                ),
            ),
        )

    @classmethod
    def from_interaction(
        cls: type[Self],
        interaction: discord.ComponentInteraction | discord.ModalInteraction,
    ) -> tuple[Self, str] | None:
        """Returns `(casino_session: Self, interaction_id: str)`"""
        try:
            casino_session_id, interaction_id = interaction.custom_id.split("_", 1)
        except ValueError:
            return None
        if len(casino_session_id) != 32:
            return None
        for casino_session in cls.cache.values():
            if casino_session.id == casino_session_id:
                return casino_session, interaction_id

    def generate_embed(self, *, entrance: bool = False) -> utils.Embed:
        embed = utils.Embed()
        embed.colour = utils.BLUE
        embed.set_author(
            name=f"{utils.clean(self.ctx.author.display_name).title()}'s Casino"
        )

        if entrance:
            embed.title = "Welcome to the casino!"
        else:
            embed.title = "Welcome back to the menu!"

        embed.description = (
            f"Hello, **{utils.clean(self.ctx.author.display_name)}**! Please select an option.\n\n"
            + self.generate_stat_description(note_invalid_stakes=True)
        )

        return embed

    async def change_stakes(self, interaction: discord.ModalInteraction):
        stakes_data: str = interaction.data["components"][0]["components"][0]["value"]  # type: ignore
        try:
            stakes = int(stakes_data)
        except ValueError:
            if stakes_data.strip().upper() not in {"MAX", "ALL", "EVERYTHING", "*"}:
                await interaction.response.send_message(
                    "That's not a valid amount to gamble lil bro try again",
                    ephemeral=True,
                )
                self.state = CasinoState.MENU
                return

            self._stakes = CasinoStakes.MAX
            await self.send(response=interaction.response, defer=True)
            self.state = CasinoState.MENU
            return

        if stakes not in range(self.MIN_STAKES, self.MAX_STAKES + 1):
            await interaction.response.send_message(
                f"You can't gamble {self.pp.format_growth(stakes, markdown=utils.MarkdownFormat.BOLD)}"
                f" bro you can only gamble {self.pp.format_growth(self.MIN_STAKES, markdown=utils.MarkdownFormat.BOLD)}"
                f" to {self.pp.format_growth(self.MAX_STAKES, markdown=utils.MarkdownFormat.BOLD)}"
                " at a time",
                ephemeral=True,
            )
            self.state = CasinoState.MENU
            return

        if stakes > self.pp.size.value:
            await interaction.response.send_message(
                f"You can't gamble {self.pp.format_growth(stakes, markdown=utils.MarkdownFormat.BOLD)}"
                f" LMAO you only have {self.pp.format_growth(self.pp.size.value, markdown=utils.MarkdownFormat.BOLD)}",
                ephemeral=True,
            )
            self.state = CasinoState.MENU
            return

        self._stakes = stakes
        await self.send(response=interaction.response, defer=True)
        self.state = CasinoState.MENU

    async def send(
        self,
        *,
        disable: bool = False,
        embed: discord.Embed | None = None,
        response: discord.InteractionResponse | None = None,
        defer: bool = False,
        external_leave: bool = False,
        entrance: bool = False,
        still_playing: bool = False,
    ) -> None:
        try:
            if external_leave:
                try:
                    await self.ctx.interaction.delete_original_message()
                except discord.HTTPException:
                    pass
            if self.state in [CasinoState.MENU, CasinoState.CHANGING_STAKES]:
                components = self.generate_menu_components()
                if disable:
                    components.disable_components()
                if response is not None:
                    if not defer:
                        await response.edit_message(
                            embed=embed or self.generate_embed(entrance=entrance),
                            components=components,
                        )
                        return
                    await response.defer_update()
                if self.ctx.interaction.response.is_done():
                    await self.ctx.interaction.edit_original_message(
                        embed=embed or self.generate_embed(entrance=entrance),
                        components=components,
                    )
                    return
                await self.ctx.interaction.response.send_message(
                    embed=embed or self.generate_embed(entrance=entrance),
                    components=components,
                )
                return
            if self.state in [CasinoState.PLAYING_DICE, CasinoState.PLAYING_BLACKJACK]:
                assert response is not None
                if disable:
                    self.game_components.disable_components()
                if response.is_done():
                    await self.ctx.interaction.edit_original_message(
                        embed=(
                            self.game_embed
                            if still_playing
                            else embed or self.generate_embed()
                        ),
                        components=self.game_components,
                    )
                    return
                await response.edit_message(
                    embed=embed or self.game_embed, components=self.game_components
                )
                return
            raise NotImplementedError("Sending in invalid state")

        # ! Really not supposed to happen either,
        # ! but just in case since we're responsible for the transaction
        except Exception as error:
            self.ctx.bot.dispatch(
                "casino_leave",
                self,
                response._parent if response is not None else self.ctx.interaction,
                error,
            )

    async def close(
        self,
        error: Exception | None = None,
        *,
        response: discord.InteractionResponse | None = None,
    ) -> None:
        self.cache.pop(self.ctx)
        embed = utils.Embed()
        embed.set_author(
            name=f"{utils.clean(self.ctx.author.display_name).title()}'s Casino"
        )
        embed.title = "Casino closed"
        embed.colour = utils.RED

        if error is None or isinstance(error, ExternalLeave):
            embed.description = f"Thank you for visiting the casino, **{utils.clean(self.ctx.author.display_name)}**!"
            embed.colour = utils.GREEN
        elif isinstance(error, asyncio.TimeoutError):
            embed.title += " - You took too long"
            embed.description = f"Next time, interact with the message within **{utils.format_time(self.TIMEOUT)}**."
        else:
            embed.title += " due to a spooky error"
            embed.description = (
                "This probably wasn't supposed to happen, you might want to report this to the staff in"
                " [our Discord server](https://discord.gg/ppbot) so we can take a closer look at it."
                f" (`{error!r}` on `STATE {self.state}`)"
            )

        embed.description += "\n\n" + self.generate_stat_description()

        try:
            await self.send(
                disable=True,
                embed=embed,
                response=response,
                external_leave=isinstance(error, ExternalLeave),
            )
        except discord.HTTPException:
            pass

    async def wait_for_interaction(
        self, *actions: str, timeout: float | None = TIMEOUT
    ) -> tuple[discord.ComponentInteraction, str]:
        """Returns `(interaction: discord.ComponentInteraction, action: str)`"""

        def check(interaction: discord.ComponentInteraction) -> bool:
            interaction_data = self.from_interaction(interaction)
            return interaction_data is not None and interaction_data[0] is self

        interaction = await self.ctx.bot.wait_for(
            "component_interaction", check=check, timeout=timeout
        )
        action = interaction.custom_id.split("_", 1)[1]

        if action not in actions:
            raise InvalidAction(action)

        return interaction, action

    async def play_dice(
        self, interaction: discord.ComponentInteraction
    ) -> tuple[discord.ComponentInteraction | None, Exception | None]:
        """Returns (interaction: discord.ComponentInteraction | None, error: Exception | None)"""
        self.state = CasinoState.PLAYING_DICE

        self.last_interaction = None

        while True:
            self.game_embed = utils.Embed()
            self.game_embed.set_author(
                name=f"{utils.clean(self.ctx.author.display_name).title()}'s game of Dice"
            )
            self.game_embed.title = (
                f"{utils.clean(self.ctx.author.display_name)} decides to roll a d12..."
            )

            roll = random.randint(1, 12)
            bot_roll = random.randint(1, 12)

            if roll > bot_roll:
                self.game_embed.colour = utils.GREEN
                self.game_embed.description = (
                    f"And wins {self.pp.format_growth(self.stakes)}!"
                )
                self.game_embed.color
                self.pp.grow(self.stakes)

            elif roll < bot_roll:
                self.game_embed.colour = utils.RED
                self.game_embed.description = (
                    f"And loses {self.pp.format_growth(self.stakes)} :("
                )
                self.pp.grow(-self.stakes)

            else:
                self.game_embed.colour = utils.BLUE
                self.game_embed.description = f"And it's a draw!"

            self.game_embed.description += "\n\n" + self.generate_stat_description(
                note_invalid_stakes=True
            )

            self.game_embed.add_field(
                name=utils.clean(self.ctx.author.display_name),
                value=f"Landed on `{roll}`",
            )

            self.game_embed.add_field(name="pp bot", value=f"Landed on `{bot_roll}`")

            self.game_components.components.clear()
            self.game_components.add_component(
                discord.ui.ActionRow(
                    discord.ui.Button(
                        label="Roll Again",
                        custom_id=f"{self.id}_REROLL",
                        style=discord.ui.ButtonStyle.green,
                        disabled=self.pp.size.value < self.stakes,
                    ),
                    discord.ui.Button(
                        label="Menu (Leave)",
                        custom_id=f"{self.id}_MENU",
                        style=discord.ui.ButtonStyle.red,
                    ),
                ),
            )

            await self.send(response=interaction.response)

            try:
                interaction, interaction_id = await self.wait_for_interaction(
                    "REROLL", "MENU", "EXTERNAL_LEAVE"
                )
            except (InvalidAction, asyncio.TimeoutError) as error:
                return None, error

            if interaction_id == "EXTERNAL_LEAVE":
                return interaction, ExternalLeave()

            if interaction_id == "MENU":
                return interaction, None

    async def play_blackjack(
        self, interaction: discord.ComponentInteraction
    ) -> tuple[discord.ComponentInteraction | None, Exception | None]:
        """Returns (interaction: discord.ComponentInteraction | None, error: Exception | None)"""
        self.state = CasinoState.PLAYING_BLACKJACK
        self.last_interaction = None

        while True:
            last_move: Literal["HIT", "STAND"] | None = None
            game_over: bool = False

            display_name = utils.clean(self.ctx.author.display_name)

            player_hand = utils.BlackjackHand()
            player_hand.add()
            player_hand.add()

            dealer_hand = utils.BlackjackHand(hide_second_card=True)
            dealer_hand.add()
            dealer_hand.add()

            actions = []

            while True:
                description = ""

                self.game_embed = utils.Embed()
                self.game_embed.set_author(
                    name=f"{display_name.title()}'s game of Blackjack"
                )
                self.game_embed.set_footer(
                    text="Deleting this message results in an automatic loss!"
                )

                if last_move == "HIT":
                    player_hand.add()
                    actions.append(
                        f"* {display_name}"
                        f" hits and receives {player_hand.cards[-1]:s}"
                    )

                player_total, player_soft = player_hand.calculate_total()
                dealer_total, dealer_soft = dealer_hand.calculate_total()

                if last_move == "STAND":
                    self.game_embed.title = "Dealer's turn"
                    if not dealer_hand.hide_second_card and dealer_total < 17:
                        dealer_hand.add()
                        actions.append(
                            f"* dealer hits and receives {dealer_hand.cards[-1]:s}"
                        )
                    dealer_hand.hide_second_card = False

                dealer_total, dealer_soft = dealer_hand.calculate_total()

                player_field_name = ""
                dealer_field_name = ""

                if player_total > 21:
                    game_over = True
                    player_field_name = "BUST! "
                    self.game_embed.color = utils.RED
                    self.game_embed.title = "YOU LOST!! loser"
                    actions.append(
                        f"- {display_name} busts."
                        f" {random.choice(["Yikes!", "RIP", "I'm boutta bussssss"])}"
                    )
                    self.pp.grow(-self.stakes)

                if dealer_total > 21:
                    last_move = None
                    game_over = True
                    dealer_field_name = "BUST! "
                    self.game_embed.title = "you won!!"
                    self.game_embed.color = utils.GREEN
                    actions.append(f"- dealer busts")
                    self.pp.grow(self.stakes)

                if 17 <= dealer_total <= 21 and last_move == "STAND":
                    last_move = None
                    game_over = True
                    if dealer_total > player_total:
                        self.game_embed.title = "YOU LOST!! loser"
                        self.game_embed.color = utils.RED
                        actions.append(
                            f"- {display_name} loses {player_total} to {dealer_total}"
                        )
                        self.pp.grow(-self.stakes)
                    elif dealer_total < player_total:
                        self.game_embed.title = "you won!!"
                        self.game_embed.color = utils.GREEN
                        actions.append(
                            f"+ {display_name} wins {player_total} to {dealer_total}"
                        )
                        self.pp.grow(self.stakes)
                    else:
                        self.game_embed.title = "PUSH"
                        self.game_embed.color = utils.BLUE
                        actions.append(f"push: {player_total} to {dealer_total}")

                if game_over:
                    dealer_hand.hide_second_card = False

                if player_soft and last_move != "STAND" and not game_over:
                    player_value = f"{player_total}/{player_total-10}"
                else:
                    player_value = str(player_total)

                if dealer_hand.hide_second_card:
                    dealer_value = "??"
                elif dealer_soft and not game_over:
                    dealer_value = f"{dealer_total}/{dealer_total-10}"
                else:
                    dealer_value = str(dealer_total)

                # self.game_embed.title = f"{utils.clean(self.ctx.author.display_name).title()}'s Turn"

                player_field_name += f"({player_value}) {utils.clean(self.ctx.author.display_name)}'s hand"
                dealer_field_name += f"({dealer_value}) pp bot's hand"

                self.game_embed.add_field(
                    name=player_field_name,
                    value=f"{player_hand:s}",
                )

                if len(actions) < 4:
                    formatted_actions = "\n".join(reversed(actions))
                else:
                    formatted_actions = "\n".join(reversed(actions[-3:]))
                    formatted_actions += f"\n({len(actions) - 3} previous action{'s' if len(actions) - 3 else ''}...)"

                if last_move != "STAND" and not game_over:
                    formatted_actions = (
                        "hit: +1 card  |  stand: dealer's turn\n\n" + formatted_actions
                    )
                elif last_move == "STAND":
                    formatted_actions = "dealer's turn\n\n" + formatted_actions

                description += f"```diff\n{formatted_actions}```"

                if game_over:
                    description += "\n" + self.generate_stat_description(
                        note_invalid_stakes=True
                    )

                self.game_embed.description = description

                self.game_embed.add_field(
                    name=dealer_field_name, value=f"{dealer_hand:s}"
                )

                self.game_components.components.clear()
                self.game_components.add_component(
                    discord.ui.ActionRow(
                        discord.ui.Button(
                            label="Hit",
                            custom_id=f"{self.id}_HIT",
                            emoji="👆",
                            style=(
                                discord.ui.ButtonStyle.blurple
                                if last_move == "HIT"
                                else discord.ui.ButtonStyle.grey
                            ),
                            disabled=self.pp.size.value < self.stakes
                            or game_over
                            or last_move == "STAND",
                        ),
                        discord.ui.Button(
                            label="Stand",
                            custom_id=f"{self.id}_STAND",
                            emoji="🤚",
                            style=(
                                discord.ui.ButtonStyle.blurple
                                if last_move == "STAND"
                                else discord.ui.ButtonStyle.grey
                            ),
                            disabled=self.pp.size.value < self.stakes
                            or game_over
                            or last_move == "STAND",
                        ),
                    ),
                )

                second_row = discord.ui.ActionRow(
                    discord.ui.Button(
                        label="Play Again",
                        custom_id=f"{self.id}_REPLAY",
                        style=discord.ui.ButtonStyle.green,
                        disabled=not game_over,
                    ),
                    discord.ui.Button(
                        label="Menu (Leave)",
                        custom_id=f"{self.id}_MENU",
                        style=discord.ui.ButtonStyle.red,
                        disabled=not game_over,
                    ),
                )

                self.game_components.add_component(second_row)

                await self.send(response=interaction.response, still_playing=True)

                if last_move == "STAND" and not game_over:
                    await asyncio.sleep(2)
                    continue

                try:
                    interaction, interaction_id = await self.wait_for_interaction(
                        "HIT", "STAND", "REPLAY", "MENU", "EXTERNAL_LEAVE"
                    )
                except (InvalidAction, asyncio.TimeoutError) as error:
                    if not game_over:
                        self.pp.grow(-self.stakes)
                    return None, error

                if interaction_id == "EXTERNAL_LEAVE":
                    return interaction, ExternalLeave()

                if interaction_id == "MENU":
                    return interaction, None

                if interaction_id == "REPLAY":
                    break

                if interaction_id == "HIT":
                    last_move = "HIT"
                elif interaction_id == "STAND":
                    last_move = "STAND"
                    actions.append(f"* {display_name} stands...")


class CasinoCommandCog(vbu.Cog[utils.Bot]):
    def __init__(self, bot: utils.Bot, logger_name: str | None = None) -> None:
        super().__init__(bot, logger_name)
        self.garbage_collector.start()

    def cog_unload(self) -> None:
        super().cog_unload()
        self.garbage_collector.cancel()

        # Force-close every open casino session
        # ? Use this instead of a direct for-loop to avoid runtime errors
        cache_keys = tuple(CasinoSession.cache.keys())

        for cache_key in cache_keys:
            # ? Cache could've been modified while looping
            try:
                casino_session = CasinoSession.cache[cache_key]
            except KeyError:
                continue

            self.bot.dispatch(
                "casino_leave", casino_session, None, asyncio.TimeoutError()
            )

    @commands.command(
        "casino",
        utils.Command,
        category=utils.CommandCategory.GAMBLING,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def casino_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Visit the casino and gamble your shit away
        """
        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)

            casino_session = CasinoSession(ctx, pp)

            async with utils.DatabaseTimeoutManager.notify(
                ctx.author.id,
                "You're still in the casino, and can't do anything else until you leave!",
                casino_id=casino_session.id,
            ):
                await casino_session.send(entrance=True)

                interaction: discord.ComponentInteraction | None
                error: commands.CommandError | None
                _, interaction, error = await self.bot.wait_for(
                    "casino_leave",
                    check=lambda s, _, _1: s is casino_session,
                )

                await casino_session.close(
                    error,
                    response=interaction.response if interaction is not None else None,
                )
                await pp.update(db.conn)

    @commands.command(
        "gamble",
        utils.Command,
        category=utils.CommandCategory.GAMBLING,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def gamble_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        (same command as /casino) Visit the casino and gamble your shit away
        """
        await self.casino_command.invoke(ctx)

    @commands.command(
        "blackjack",
        utils.Command,
        category=utils.CommandCategory.GAMBLING,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def blackjack_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        (same command as /casino) Visit the casino and gamble your shit away
        """
        await self.casino_command.invoke(ctx)

    @vbu.Cog.listener("on_component_interaction")
    async def casino_component_interaction_handler(
        self, interaction: discord.ComponentInteraction
    ) -> None:
        casino_session_data = CasinoSession.from_interaction(interaction)
        if casino_session_data is None:
            return
        casino_session, interaction_id = casino_session_data
        if casino_session.ctx.author.id != interaction.user.id:
            return

        try:
            if casino_session.state in [CasinoState.MENU, CasinoState.CHANGING_STAKES]:
                if interaction_id == "STAKES":
                    casino_session.last_interaction = datetime.now(UTC).replace(
                        tzinfo=None
                    )
                    casino_session.state = CasinoState.CHANGING_STAKES
                    await interaction.response.send_modal(
                        discord.ui.Modal(
                            title="Changing casino stakes",
                            custom_id=f"{casino_session.id}_CHANGING_STAKES",
                            components=[
                                discord.ui.ActionRow(
                                    discord.ui.InputText(
                                        label="How many inches do you want to gamble?",
                                        custom_id=f"{casino_session.id}_STAKES",
                                        style=discord.TextStyle.long,
                                        placeholder=f"{casino_session.MIN_STAKES} - {casino_session.MAX_STAKES}",
                                        min_length=min(
                                            3,
                                            len(
                                                utils.format_int(
                                                    casino_session.MIN_STAKES,
                                                    utils.IntFormatType.FULL,
                                                )
                                            ),
                                        ),
                                        max_length=max(
                                            3,
                                            len(
                                                utils.format_int(
                                                    casino_session.MAX_STAKES,
                                                    utils.IntFormatType.FULL,
                                                )
                                            ),
                                        ),
                                    )
                                )
                            ],
                        )
                    )
                    return
                if interaction_id == "EXTERNAL_LEAVE":
                    self.bot.dispatch(
                        "casino_leave", casino_session, interaction, ExternalLeave()
                    )
                    return
                if interaction_id == "LEAVE":
                    self.bot.dispatch("casino_leave", casino_session, interaction, None)
                    return
                if interaction_id in ["DICE", "BLACKJACK"]:
                    if interaction_id == "DICE":
                        result_interaction, result_error = (
                            await casino_session.play_dice(interaction)
                        )
                    else:
                        result_interaction, result_error = (
                            await casino_session.play_blackjack(interaction)
                        )

                    if result_error is not None:
                        self.bot.dispatch(
                            "casino_leave",
                            casino_session,
                            (
                                result_interaction
                                if result_interaction is not None
                                else interaction
                            ),
                            result_error,
                        )
                        return
                    if result_interaction is None:  # ! Not supposed to ever happen!
                        self.bot.dispatch(
                            "casino_leave",
                            casino_session,
                            interaction,
                            Exception("The code fucked up"),
                        )
                        return
                    casino_session.last_interaction = datetime.now(UTC).replace(
                        tzinfo=None
                    )
                    casino_session.state = CasinoState.MENU
                    await casino_session.send(response=result_interaction.response)
                    return

        # ! Really not supposed to happen either,
        # ! but just in case since we're responsible for the transaction
        except Exception as error:
            self.bot.dispatch(
                "casino_leave",
                casino_session,
                interaction,
                error,
            )
            return

    @vbu.Cog.listener("on_modal_submit")
    async def casino_modal_submit_handler(
        self, interaction: discord.ModalInteraction
    ) -> None:
        casino_session_data = CasinoSession.from_interaction(interaction)
        if casino_session_data is None:
            return
        casino_session, interaction_id = casino_session_data
        if casino_session.ctx.author.id != interaction.user.id:
            return

        casino_session.last_interaction = datetime.now(UTC).replace(tzinfo=None)

        if (
            casino_session.state == CasinoState.CHANGING_STAKES
            and interaction_id == "CHANGING_STAKES"
        ):
            try:
                await casino_session.change_stakes(interaction)
            except discord.HTTPException as error:
                self.bot.dispatch("casino_leave", casino_session, None, error)
            return
        self.bot.dispatch(
            "casino_leave",
            casino_session,
            interaction,
            NotImplementedError(3, interaction_id),
        )

    @tasks.loop(seconds=1)
    async def garbage_collector(self) -> None:
        # ? Use this instead of a direct for-loop to avoid runtime errors
        cache_keys = tuple(CasinoSession.cache.keys())

        for cache_key in cache_keys:
            # ? Cache could've been modified while looping
            try:
                casino_session = CasinoSession.cache[cache_key]
            except KeyError:
                continue

            if casino_session.last_interaction is None:
                continue

            if datetime.now(UTC).replace(
                tzinfo=None
            ) - casino_session.last_interaction < timedelta(seconds=30):
                continue

            self.bot.dispatch(
                "casino_leave", casino_session, None, asyncio.TimeoutError()
            )


async def setup(bot: utils.Bot):
    await bot.add_cog(CasinoCommandCog(bot))
