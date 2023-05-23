import random

from discord.ext import commands, vbu
from . import utils


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

    @commands.command(
        "beg",
        utils.Command,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.is_slash_command()
    async def beg_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Beg for some inches
        """
        async with self.bot.database() as db, db.conn.transaction():
            try:
                pp = await utils.Pp.fetch(
                    db.conn,
                    {"user_id": ctx.author.id},
                    lock=utils.RowLevelLockMode.FOR_UPDATE,
                )
            except utils.RecordNotFoundError:
                raise commands.CheckFailure("You don't have a pp!")

            donator = random.choice(list(self.DONATORS))
            embed = utils.Embed()

            if random.randint(0, 5):
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
