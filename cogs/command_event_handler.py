import asyncio
import random
from enum import Flag, auto

import discord
from discord.ext import commands, vbu

from . import utils


class TipsGiven(Flag):
    BUY_PILL = auto()


class CommandEventHandlerCog(vbu.Cog):
    tips_given_cache: dict[int, TipsGiven] = {}

    async def send_buy_pill_tip(self, ctx: commands.SlashContext[vbu.Bot]) -> None:
        embed = utils.Embed(color=utils.PINK)
        embed.title = "Time for an upgrade!!"
        embed.description = (
            "Good job on getting your first 60 inches!"
            " At this point, it'll be **VERY BENEFICIAL** for you to cop yourself some"
            " **pills**. These can be purchased via `/buy pills 1` for 60 inches, and"
            " will **DOUBLE** your pp production! Learn more about these pills at"
            f" {utils.format_slash_command("shop")}."
        )

        await ctx.interaction.followup.send(embed=embed, ephemeral=True)

    @vbu.Cog.listener("on_command")
    async def log_command(
        self, ctx: commands.Context[vbu.Bot] | commands.SlashContext[vbu.Bot]
    ):
        if ctx.command is None:
            return

        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
        ):
            await utils.CommandLog.increment(db.conn, ctx.command.name)

    @vbu.Cog.listener("on_command")
    async def give_changelog_updates(
        self, ctx: commands.Context[vbu.Bot] | commands.SlashContext[vbu.Bot]
    ):
        if not isinstance(ctx, commands.SlashContext):
            return

        async with utils.DatabaseWrapper() as db:
            try:
                pp_extras = await utils.PpExtras.fetch_from_user(
                    db.conn, user_id=ctx.author.id, edit=True
                )
            except utils.DatabaseTimeout:
                return

            if utils.ChangelogManager.is_old_version(
                pp_extras.last_played_version.value
            ):
                pp_extras.last_played_version.value = (
                    utils.ChangelogManager.latest_version
                )
                await pp_extras.update(db.conn)

        embed = utils.Embed(color=utils.PINK)
        latest_version = utils.ChangelogManager.latest_version
        version_changelog = utils.ChangelogManager.changelog[latest_version]

        embed.set_author(name=f"NEW PP BOT UPDATE - V{latest_version}")
        embed.title = version_changelog["title"]
        embed.description = version_changelog["description"]

    @vbu.Cog.listener("on_command")
    async def give_relevant_tips(
        self, ctx: commands.Context[vbu.Bot] | commands.SlashContext[vbu.Bot]
    ):
        if not isinstance(ctx, commands.SlashContext):
            return

        if not isinstance(ctx.command, utils.Command):
            return

        if ctx.command.category != utils.CommandCategory.GROWING_PP:
            return

        async with utils.DatabaseWrapper() as db:
            try:
                pp = await utils.Pp.fetch_from_user(db.conn, user_id=ctx.author.id)
            except (utils.PpMissing, utils.DatabaseTimeout):
                return

        # Do this because interactions can only be responded to once and
        # followups can only be sent after a response
        tries = 0
        while True:
            if ctx.interaction.response.is_done():
                break

            tries += 1
            if tries == 3:
                return

            await asyncio.sleep(1)

        if pp.multiplier.value == 1 and pp.size.value >= 60:
            try:
                tips_given = self.tips_given_cache[ctx.author.id]
            except KeyError:
                tips_given = TipsGiven(0)

            if TipsGiven.BUY_PILL in tips_given:
                if random.randint(1, 5) == 1:
                    await self.send_buy_pill_tip(ctx)
            else:
                self.tips_given_cache[ctx.author.id] = tips_given | TipsGiven.BUY_PILL
                await self.send_buy_pill_tip(ctx)


async def setup(bot: vbu.Bot):
    x = CommandEventHandlerCog(bot)
    await bot.add_cog(x)
