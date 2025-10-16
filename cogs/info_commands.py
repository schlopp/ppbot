import asyncio
import random

import discord
from discord.ext import commands, vbu

from . import utils


class HelpCommandsCog(vbu.Cog[utils.Bot]):
    INVITE_URL = "https://discord.com/api/oauth2/authorize?client_id=735147633076863027&permissions=517543939136&scope=bot%20applications.commands"
    QUOTES = [
        "wtf is this bot",
        "i love my wife",
        "schlopp is SO HOT",
        "my gf has a bigger pp than me",
    ]

    def generate_help_embed(self) -> utils.Embed:
        embed = utils.Embed()
        embed.color = utils.BLUE
        embed.title = "u need some help?"
        embed.url = utils.MEME_URL
        embed.set_footer(text=f'"{random.choice(self.QUOTES)}"')

        for category in utils.CommandCategory:
            category_commands: list[commands.Command] = []
            for command in self.bot.commands:
                if command.hidden:
                    continue

                if not command.application_command_meta:
                    continue

                if isinstance(command, utils.Command):
                    if command.category == category:
                        category_commands.append(command)

                elif category == utils.CommandCategory.OTHER:
                    category_commands.append(command)

            if not category_commands:
                continue

            category_commands.sort(key=lambda c: c.name)

            text = " ".join(
                utils.format_slash_command(command.name)
                for command in category_commands
            )
            embed.add_field(name=category.value, value=text)

        return embed

    def generate_new_user_embed(self) -> utils.Embed:
        embed = utils.Embed()
        embed.color = utils.PINK

        embed.set_author(name="IMPORTANT!!!!!1!!")
        embed.title = "u dont have a pp yet!!!"
        embed.url = f"{utils.MEME_URL}#"

        embed.description = (
            f"use {utils.format_slash_command('new')}"
            " to make a pp and start growing it :)"
        )

        return embed

    @commands.command(
        "help",
        utils.Command,
        category=utils.CommandCategory.HELP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def help_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Need some help? Here you go :)
        """

        await ctx.interaction.response.send_message(embed=self.generate_help_embed())

        async with utils.DatabaseWrapper() as db:
            try:
                await utils.Pp.fetch_from_user(db.conn, ctx.author.id)
            except utils.PpMissing:
                await ctx.interaction.followup.send(
                    embed=self.generate_new_user_embed(), ephemeral=True
                )

    @commands.command(
        "invite",
        utils.Command,
        category=utils.CommandCategory.HELP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def invite_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Invite pp bot to your server!! NOW!!!!!!
        """

        embed = utils.Embed(color=utils.PINK)
        embed.description = (
            f"**INVITE ME !!! [PLEASE!!!!!!!!!!!]({self.INVITE_URL})"
            " I WANNA BE IN YOUR SERVER!!!!**"
        )

        action_row = discord.ui.ActionRow(
            discord.ui.Button(
                label="Invite me!!!",
                emoji="<:ppMalding:902894208795435031>",
                style=discord.ButtonStyle.url,
                url=self.INVITE_URL,
            )
        )

        components = discord.ui.MessageComponents(action_row)

        await ctx.interaction.response.send_message(
            embed=embed,
            components=components,
        )

        await asyncio.sleep(2)

        action_row.add_component(
            discord.ui.Button(
                label="Invite me (evil version)",
                emoji="<:ppevil:871396299830861884>",
                style=discord.ButtonStyle.url,
                url=self.INVITE_URL,
            )
        )

        try:
            await ctx.interaction.edit_original_message(components=components)
        except discord.HTTPException:
            return

        await asyncio.sleep(5)

        action_row.add_component(
            discord.ui.Button(
                label="Invite me (SUPER evil version)",
                emoji="<:ppevil:871396299830861884>",
                style=discord.ButtonStyle.url,
                url=self.INVITE_URL,
            )
        )

        try:
            await ctx.interaction.edit_original_message(components=components)
        except discord.HTTPException:
            return

    @commands.command(
        "vote",
        utils.Command,
        category=utils.CommandCategory.HELP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def vote_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Vote and get 4x MULTIPLIER INCREASE!!! (free ofcourse)
        """

        embed = utils.Embed(color=utils.PINK)
        embed.description = (
            f"**VOTE NOW !!! [PLEASE!!!!!!!!!!!]({utils.VOTE_URL})"
            " I WANNA BE VOTED FOR!!!!**"
            "\n\n"
            "Voting is free and gives you:"
            f"\n- a [**300% multiplier increase**]({utils.VOTE_URL})"
            f"\n- [**shorter cooldowns**]({utils.VOTE_URL})"
            f"\n- [**a LOT of inches**]({utils.VOTE_URL})"
            f"\n- {random.choice([
                "love from your parents",
                "two packs of Malboro Reds",
                "a discord kitten",
                "a girlfriend (real)",
                "free head whenever u want",
                "a new therapist",
                "pp bot bathwater",
                "5 big booms",
            ])}"
        )

        action_row = discord.ui.ActionRow(
            discord.ui.Button(
                label="Vote!!!",
                emoji="<:ppMalding:902894208795435031>",
                style=discord.ButtonStyle.url,
                url=utils.VOTE_URL,
            )
        )

        components = discord.ui.MessageComponents(action_row)

        await ctx.interaction.response.send_message(
            embed=embed,
            components=components,
        )

        await asyncio.sleep(2)

        action_row.add_component(
            discord.ui.Button(
                label="vote (evil version)",
                emoji="<:ppevil:871396299830861884>",
                style=discord.ButtonStyle.url,
                url=utils.VOTE_URL,
            )
        )

        try:
            await ctx.interaction.edit_original_message(components=components)
        except discord.HTTPException:
            return

        await asyncio.sleep(5)

        action_row.add_component(
            discord.ui.Button(
                label="vote (SUPER evil version)",
                emoji="<:ppevil:871396299830861884>",
                style=discord.ButtonStyle.url,
                url=utils.VOTE_URL,
            )
        )

        try:
            await ctx.interaction.edit_original_message(components=components)
        except discord.HTTPException:
            return

        await asyncio.sleep(10)

        action_row.components.pop()
        action_row.components.pop()

        try:
            await ctx.interaction.edit_original_message(components=components)
        except discord.HTTPException:
            return

    @commands.command(
        "server",
        utils.Command,
        category=utils.CommandCategory.HELP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def server_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Join the official pp bot Discord server for updates giveaways and leaks!!
        """

        embed = utils.Embed(color=utils.PINK)
        embed.description = (
            f"**[JOIN THE PP CULT!!!](https://discord.gg/ppbot)"
            " WE WANT YOU!!!!!**"
            "\n\n"
            "Joining our server gives you:"
            f"\n- [**early-access**](https://discord.gg/ppbot) to pp bot updates"
            f"\n- exclusive [**giveaways**](https://discord.gg/ppbot)"
            f"\n- update [**leaks**](https://discord.gg/ppbot)"
            f"\n- {random.choice([
                "love from your parents",
                "two packs of Malboro Reds",
                "a discord kitten",
                "a girlfriend (real)",
                "free head whenever u want",
                "a new therapist",
                "pp bot bathwater",
                "5 big booms",
            ])}"
        )

        action_row = discord.ui.ActionRow(
            discord.ui.Button(
                label="JOIN!!!",
                emoji="<:ppMalding:902894208795435031>",
                style=discord.ButtonStyle.url,
                url="https://discord.gg/ppbot",
            )
        )

        components = discord.ui.MessageComponents(action_row)

        await ctx.interaction.response.send_message(
            "discord.gg/ppbot",
            embed=embed,
            components=components,
        )

        await asyncio.sleep(2)

        action_row.add_component(
            discord.ui.Button(
                label="join (evil version)",
                emoji="<:ppevil:871396299830861884>",
                style=discord.ButtonStyle.url,
                url="https://discord.gg/ppbot",
            )
        )

        try:
            await ctx.interaction.edit_original_message(components=components)
        except discord.HTTPException:
            return

        await asyncio.sleep(5)

        action_row.add_component(
            discord.ui.Button(
                label="join (SUPER evil version)",
                emoji="<:ppevil:871396299830861884>",
                style=discord.ButtonStyle.url,
                url="https://discord.gg/ppbot",
            )
        )

        try:
            await ctx.interaction.edit_original_message(components=components)
        except discord.HTTPException:
            return

        await asyncio.sleep(10)

        action_row.components.pop()
        action_row.components.pop()

        try:
            await ctx.interaction.edit_original_message(components=components)
        except discord.HTTPException:
            return


async def setup(bot: utils.Bot):
    await bot.add_cog(HelpCommandsCog(bot))
