import random

from discord.ext import commands, vbu

from . import utils


class HelpCommandsCog(vbu.Cog[utils.Bot]):
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


async def setup(bot: utils.Bot):
    await bot.add_cog(HelpCommandsCog(bot))
