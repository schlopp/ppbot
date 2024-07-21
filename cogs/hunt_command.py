import enum
import random
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
            list(Activity), weights=list(activity.value for activity in Activity)
        )[0]


MinigameActivity = Literal[Activity.CLICK_THAT_BUTTON_MINIGAME]


class HuntCommandCog(vbu.Cog[utils.Bot]):
    HUNTING_OPTIONS: dict[str, range] = {
        "shot a homeless man": range(1, 21),
        "deadass just killed a man": range(5, 21),
        "shot up a mall": range(5, 21),
        "hijacked a fucking orphanage and sold all the kids": range(30, 51),
        "KILLED THE PP GODS": range(50, 101),
    }

    ITEM_BREAK_RESPONSES: list[str] = [
        "{} got arrested and their rifle got confiscated!!1!",
    ]

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
            Activity.CLICK_THAT_BUTTON_MINIGAME: utils.ClickThatButtonMinigame,
        }

        minigame_type = minigame_types[minigame_activity]
        minigame = minigame_type(
            bot=bot,
            connection=connection,
            pp=pp,
            context=minigame_type.generate_random_dialogue("hunt"),
        )

        await minigame.start(interaction)

    def get_hunting_option(self) -> tuple[str, int]:
        """Returns `(hunting_option: str, growth: int)`"""
        worth_index = random.randrange(0, len(self.HUNTING_OPTIONS))
        hunting_option = list(self.HUNTING_OPTIONS)[worth_index]
        growth = random.choice(self.HUNTING_OPTIONS[hunting_option])

        worth = worth_index / (len(self.HUNTING_OPTIONS) - 1)

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
    @commands.cooldown(1, 60, commands.BucketType.user)
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

            embed = utils.Embed()

            if activity == Activity.RIFLE_BREAK:
                inv_tool = await utils.InventoryItem.fetch(
                    db.conn,
                    {"user_id": ctx.author.id, "id": tool.id},
                    lock=utils.RowLevelLockMode.FOR_UPDATE,
                )
                inv_tool.amount.value -= 1
                await inv_tool.update(db.conn)

                embed.colour = utils.RED
                embed.description = random.choice(self.ITEM_BREAK_RESPONSES).format(
                    ctx.author.mention
                ) + (
                    f"\n\n(You now have {inv_tool.format_item(article=utils.Article.NUMERAL)}"
                    " left)"
                )

                if inv_tool.amount.value == 0:
                    embed.description += " 😢"

            elif activity == Activity.SUCCESS:
                option, growth = self.get_hunting_option()
                pp.grow_with_multipliers(
                    growth,
                    voted=await pp.has_voted(),
                )

                embed.colour = utils.GREEN
                embed.description = (
                    f"**{ctx.author.mention}** {option} and for {pp.format_growth()}!"
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
