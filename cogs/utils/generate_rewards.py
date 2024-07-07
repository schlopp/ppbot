import itertools
import random
from collections.abc import Callable

import asyncpg

from . import Pp, InventoryItem, ItemManager, format_iterable


async def give_random_reward(
    connection: asyncpg.Connection,
    pp: Pp,
    *,
    growth_range: tuple[int, int],
    max_item_reward_price: int,
    formatter: Callable[[list[str]], str] = lambda segments: format_iterable(
        segments, inline=True
    ),
) -> tuple[str, int, dict[InventoryItem, int]]:
    """
    Returns `(message: str, growth: int, reward_items: dict[reward_item: InventoryItem, amount: int])`
    """
    segments: list[str] = []

    growth = pp.grow_with_multipliers(
        random.randint(*growth_range),
        voted=await pp.has_voted(),
    )
    await pp.update(connection)
    segments.append(pp.format_growth())

    reward_item_ids: list[str] = []
    reward_items: dict[InventoryItem, int] = {}

    while True:
        # 100% chance of 1+ items
        # 50% chance of 2+ items
        # 17% chance of 3+ items
        # 4% chance of 4+ items
        # etc..
        if reward_item_ids and random.randint(0, len(reward_item_ids)):
            break
        try:
            reward_item = InventoryItem(
                pp.user_id,
                random.choice(
                    [
                        item_id
                        for item_id, item in itertools.chain(
                            ItemManager.tools.items(),
                            ItemManager.useless.items(),
                            ItemManager.buffs.items(),
                        )
                        if item.price < max_item_reward_price * pp.multiplier.value
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
            max_item_reward_price * pp.multiplier.value // reward_item.item.price * 3,
        )

        reward_items[reward_item] = reward_item.amount.value

        await reward_item.update(connection, additional=True)
        reward_item_ids.append(reward_item.id)
        segments.append(
            reward_item.format_item(article=reward_item.item.indefinite_article)
        )

    return formatter(segments), growth, reward_items
