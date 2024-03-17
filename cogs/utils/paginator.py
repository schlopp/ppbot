import math
import uuid
from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar, Self, Generic, cast, Literal

import discord

from . import Object, Embed, Bot


PaginatorActions = Literal["START", "PREVIOUS", "NEXT", "END"]
CategorisedPaginatorActions = PaginatorActions | Literal["SELECT_CATEGORY"]
_ItemT = TypeVar("_ItemT")
_ActionsT = TypeVar("_ActionsT", bound=str)


class Paginator(Object, Generic[_ItemT, _ActionsT]):
    def __init__(
        self,
        bot: Bot,
        items: Iterable[_ItemT],
        *,
        loader: Callable[[Self, tuple[_ItemT, ...]], Awaitable[Embed]],
        per_page: int = 5,
    ) -> None:
        self.bot = bot
        self._items = items
        self.loader = loader
        self.per_page = per_page
        self.current_page = 0
        self.max_pages = math.ceil(len(self.items) / self.per_page)
        self.id = uuid.uuid4().hex
        self._paginator_action_row = discord.ui.ActionRow(
            discord.ui.Button(
                custom_id=f"{self.id}_START",
                emoji="<:start:1108655615410196520>",
                disabled=True,
            ),
            discord.ui.Button(
                custom_id=f"{self.id}_PREVIOUS",
                emoji="<:previous:1108442605718610051>",
                disabled=True,
            ),
            discord.ui.Button(
                custom_id=f"{self.id}_NEXT", emoji="<:next:1108442607039811735>"
            ),
            discord.ui.Button(
                custom_id=f"{self.id}_END", emoji="<:end:1108655617029193740>"
            ),
        )
        self._components = discord.ui.MessageComponents(self._paginator_action_row)

    @property
    def items(self) -> tuple[_ItemT, ...]:
        """Returns `(item: _ItemT, ...)`"""
        return tuple(self._items)

    def _update_components(self, *, disable_all: bool = False) -> None:
        if disable_all:
            self._components.disable_components()
            return

        self._components.enable_components()
        buttons = cast(
            list[discord.ui.Button],
            self._paginator_action_row.components,
        )

        start_button = buttons[0]
        previous_button = buttons[1]
        next_button = buttons[2]
        end_button = buttons[3]

        if not self.current_page:
            start_button.disable()
            previous_button.disable()

        if self.current_page + 1 == self.max_pages:
            next_button.disable()
            end_button.disable()

    def _get_current_items(self) -> tuple[_ItemT, ...]:
        """Returns `(current_item: _ItemT, ...)`"""
        return self.items[
            self.current_page * self.per_page : (self.current_page + 1) * self.per_page
        ]

    async def wait_for_interaction(
        self, user: discord.User | discord.Member
    ) -> tuple[discord.ComponentInteraction, _ActionsT]:
        """Returns `(component_interaction: discord.ComponentInteraction, action: _ActionsT)`"""
        component_interaction = await self.bot.wait_for(
            "component_interaction",
            check=lambda i: i.user == user and i.custom_id.startswith(self.id),
            timeout=180,
        )
        return component_interaction, cast(
            _ActionsT,
            component_interaction.custom_id.split("_", 1)[1],
        )

    def handle_interaction(
        self,
        interaction: discord.ComponentInteraction,  # keep for subclass customisability
        action: _ActionsT,
    ):
        if action == "START":
            self.current_page = 0
        elif action == "PREVIOUS":
            self.current_page -= 1
        elif action == "NEXT":
            self.current_page += 1
        elif action == "END":
            self.current_page = self.max_pages - 1

    async def start(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=await self.loader(self, self._get_current_items()),
            components=self._components,
        )

        while True:
            try:
                component_interaction, action = await self.wait_for_interaction(
                    interaction.user
                )
            except TimeoutError:
                self._update_components(disable_all=True)
                await interaction.edit_original_message(components=self._components)
                return

            self.handle_interaction(component_interaction, action)

            self._update_components()
            await component_interaction.response.edit_message(
                embed=await self.loader(self, self._get_current_items()),
                components=self._components,
            )


class CategorisedPaginator(Paginator[_ItemT, CategorisedPaginatorActions]):
    def __init__(
        self,
        bot: Bot,
        items: Iterable[_ItemT],
        *,
        categories: dict[str, str],
        loader: Callable[[Self, tuple[_ItemT, ...]], Awaitable[Embed]],
        categoriser: Callable[[_ItemT, set[str]], bool],
        per_page: int = 5,
    ) -> None:
        # Has to be defined before super() due to (indirect) usage in superclass __init__
        self.active_categories: set[str] = {"ALL"}

        super().__init__(bot, items, loader=loader, per_page=per_page)
        self.categories = categories
        self.categoriser = categoriser

        self.category_options = [
            discord.ui.SelectOption(label="All", value="ALL", default=True)
        ]

        for category, category_name in self.categories.items():
            self.category_options.append(
                discord.ui.SelectOption(
                    label=category_name,
                    value=category,
                    default=False,
                )
            )

        self._paginator_category_select_menu = discord.ui.SelectMenu(
            custom_id=f"{self.id}_SELECT_CATEGORY",
            options=self.category_options,
            placeholder="Categories",
            max_values=len(self.category_options),
        )

        self._components.components.insert(
            0, discord.ui.ActionRow(self._paginator_category_select_menu)
        )

    def _update_components(self, *, disable_all: bool = False) -> None:
        super()._update_components(disable_all=disable_all)
        if disable_all:
            return

        for category_option in self._paginator_category_select_menu.options:
            if category_option.value in self.active_categories:
                category_option.default = True
                continue
            category_option.default = False

    def handle_interaction(
        self,
        interaction: discord.ComponentInteraction,
        action: CategorisedPaginatorActions,
    ) -> None:
        if action == "SELECT_CATEGORY":
            categories = interaction.data.get("values")
            assert categories is not None

            # Only use category "ALL" if every single category is individually selected
            if len(categories) >= len(self.category_options) - 1:
                self.active_categories = {"ALL"}

            elif "ALL" in categories:
                if "ALL" in self.active_categories:
                    self.active_categories = set(categories) - {"ALL"}
                else:
                    self.active_categories = {"ALL"}

            else:
                self.active_categories = set(categories)

            self.max_pages = math.ceil(len(self.items) / self.per_page)
            self.current_page = min(self.current_page, self.max_pages - 1)

        else:
            super().handle_interaction(interaction, action)

    @property
    def items(self) -> tuple[_ItemT, ...]:
        return tuple(
            item
            for item in self._items
            if "ALL" in self.active_categories
            or self.categoriser(item, self.active_categories)
        )
