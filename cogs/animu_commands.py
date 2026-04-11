import asyncio
import random
import aiohttp
from typing import Literal, TypedDict

import discord
from discord.ext import commands, vbu

from . import utils

AnimuLiterals = Literal[
    "nom",
    "poke",
    "cry",
    "kiss",
    "pat",
    "hug",
    "wink",
    "face-palm",
    "custom_punch",
]


class AnimuPayload(TypedDict):
    link: str
    type: str


class AnimuCommandsCog(vbu.Cog[utils.Bot]):
    BASE_URL = "https://api.some-random-api.com"
    animu_payload_cache: dict[AnimuLiterals, list[str]] = {
        "custom_punch": [
            "https://c.tenor.com/XEyGgxnqtmYAAAAd/punch-beat-up.gif",
            "https://c.tenor.com/FFYqOVVbrJAAAAAC/markiplier-punch.gif",
            "https://c.tenor.com/LefsQCyZCi8AAAAd/cry-rage.gif",
            "https://c.tenor.com/DyqH3PQFYpsAAAAC/burn.gif",
            "https://c.tenor.com/YOHIKDO0MZgAAAAC/rejection-kids.gif",
        ]
    }

    async def fetch_animu(
        self,
        animu: AnimuLiterals,
    ) -> str:
        # for custom stuff that isnt via SRA
        if animu == "custom_punch":
            return random.choice(self.animu_payload_cache[animu])

        async with aiohttp.ClientSession() as session:
            endpoint = f"{self.BASE_URL}/animu/{animu}"
            async with session.get(endpoint) as response:
                if response.status != 200:
                    self.logger.warning(
                        f"Received {response.status} from endpoint {endpoint}"
                    )
                    try:
                        gif = random.choice(self.animu_payload_cache[animu])
                    except:
                        raise Exception(
                            f"{endpoint} raised {response.status} and {animu!r} cache is empty"
                        )

                payload: AnimuPayload = await response.json()
                gif = payload["link"]

                try:
                    self.animu_payload_cache[animu].append(gif)
                except KeyError:
                    self.animu_payload_cache[animu] = [gif]

                return gif

    async def send_animu_embed(
        self,
        ctx: commands.SlashContext[utils.Bot],
        animu: AnimuLiterals,
        initiator: discord.Member | discord.User,
        target: discord.Member | discord.User | None,
        titles: list[str],
        footers: list[str] | None = None,
    ) -> None:
        gif = await self.fetch_animu(animu)
        print(gif)

        title = random.choice(titles)

        embed = utils.Embed()
        embed.set_image(url=gif)

        if target is not None:
            embed.title = title.format(
                initiator=initiator.display_name, target=target.display_name
            )
        else:
            embed.title = title.format(initiator=initiator.display_name)

        if footers is not None:
            embed.set_footer(text=random.choice(footers))

        if target is not None:
            await ctx.interaction.response.send_message(
                f"-# {title.format(initiator=initiator.mention, target=target.mention)}",
                embed=embed,
            )
        else:
            await ctx.interaction.response.send_message(
                embed=embed,
            )

    @commands.command(
        "bite",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="who",
                    type=discord.ApplicationCommandOptionType.user,
                    description="who r u biting? freak",
                )
            ]
        ),
    )
    @commands.is_slash_command()
    async def bite_command(
        self, ctx: commands.SlashContext[utils.Bot], who: discord.Member | discord.User
    ) -> None:
        """
        hope nobody gets hurt
        """

        if who == ctx.author:
            titles: list[str] = [
                "yeah go for it, bite urself",
                "kinda weird to be biting urself",
                "so u just like biting urself?",
                "decides clone themselves and starts biting",
            ]
        else:
            titles = [
                "{initiator} takes a big ol' bite outta {target}",
                "{initiator} turns into a vampire on {target}",
                "{initiator} softly bites {target}",
                "{initiator} bites {target} and nobody knows why",
                "{initiator} suddenly bites {target}",
            ]

        if who == ctx.bot.user:
            footers: list[str] | None = [
                "how dare you bite pp bot. 20 LASHINGS",
                "biting pp bot is illegal",
                "do NOT bite pp bot",
                "it is very rude to bite pp bot",
            ]
        else:
            footers = None

        await self.send_animu_embed(
            ctx,
            "nom",
            ctx.author,
            who,
            titles,
            footers,
        )

    @commands.command(
        "poke",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="who",
                    type=discord.ApplicationCommandOptionType.user,
                    description="who r u poking? rude",
                )
            ]
        ),
    )
    @commands.is_slash_command()
    async def poke_command(
        self, ctx: commands.SlashContext[utils.Bot], who: discord.Member | discord.User
    ) -> None:
        """
        very VERY annoying
        """

        if who == ctx.author:
            titles: list[str] = [
                "poking urself is kinda lame",
                "dont u have anyone else to poke?",
                "so u just like poking urself?",
                "decides clone themselves and starts poking",
            ]
        else:
            titles = [
                "{initiator} pokes {target} just to see what happens",
                "{initiator} gives {target} a quick poke",
                "{initiator} softly pokes {target}",
                "{initiator} pokes {target} and immediately regrets it",
                "{initiator} suddenly pokes {target}",
                "{initiator} pokes {target} for absolutely no reason",
            ]

        if who == ctx.bot.user:
            footers: list[str] | None = [
                "how dare you poke pp bot. 20 LASHINGS",
                "poking pp bot is illegal",
                "do NOT poke pp bot",
                "it is very rude to poke pp bot",
            ]
        else:
            footers = None

        await self.send_animu_embed(
            ctx,
            "poke",
            ctx.author,
            who,
            titles,
            footers,
        )

    @commands.command(
        "cry",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def cry_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        when ur in TEARS and SOBBING :(
        """

        titles: list[str] = [
            "{initiator} cries alone in the corner",
            "{initiator} bursts into tears",
            "{initiator} lets out a sad sob",
            "{initiator} can't hold back the tears",
            "{initiator} weeps quietly",
            "{initiator} cries for absolutely no reason",
            "{initiator} is fucking SOBBING😭😭😭😭😭",
            "{initiator} is COOKED😭😭😭😭😭",
            "{initiator} is sad as hell😭😭😭😭😭",
            "{initiator} ugly cries😭😭",
            "{initiator} cries and NOBODY CARES😂😂😂😂😂😂😂",
        ]

        await self.send_animu_embed(
            ctx,
            "cry",
            ctx.author,
            None,
            titles,
            None,
        )

    @commands.command(
        "kiss",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="who",
                    type=discord.ApplicationCommandOptionType.user,
                    description="who r u kissing? how romantic",
                )
            ],
        ),
    )
    @commands.is_slash_command()
    async def kiss_command(
        self, ctx: commands.SlashContext[utils.Bot], who: discord.Member | discord.User
    ) -> None:
        """
        give someone a smooch
        """

        animu: AnimuLiterals = "kiss"

        if who == ctx.author:
            titles: list[str] = [
                "kissing urself is kinda sad ngl",
                "dont u have anyone else to kiss?",
                "so u just like kissing urself?",
                "how egocentric of u",
                "how does that even work",
            ]
        elif who.id in self.bot.owner_ids:
            titles = [
                "{initiator} is not POWERFUL enough to kiss {target}",
                "{initiator} is NOT COOL ENOUGH to kiss {target}",
                "{target} is way too cool for {initiator}",
            ]
            animu = "custom_punch"
        else:
            titles = [
                "{initiator} gives {target} a sweet little kiss",
                "{initiator} smooches {target} on the cheek",
                "{initiator} plants a big kiss on {target}",
                "{initiator} steals a kiss from {target}",
                "{initiator} kisses {target} like in a rom-com",
                "{initiator} lovingly kisses {target}",
                "{initiator} has a full on makeout session with {target}",
                "{initiator} and {target} kiss extremely passionately",
            ]

        if who == ctx.bot.user:
            footers: list[str] | None = [
                "how dare you kiss pp bot. 20 LASHINGS",
                "kissing pp bot is illegal",
                "do NOT kiss pp bot",
                "it is very rude to kiss pp bot",
                "pp bot is super flustered by ur kiss",
            ]
        else:
            footers = None

        await self.send_animu_embed(
            ctx,
            animu,
            ctx.author,
            who,
            titles,
            footers,
        )

    @commands.command(
        "pat",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="who",
                    type=discord.ApplicationCommandOptionType.user,
                    description="whos a good boy? whos a good boy?? u are!!!",
                )
            ]
        ),
    )
    @commands.is_slash_command()
    async def pat_command(
        self, ctx: commands.SlashContext[utils.Bot], who: discord.Member | discord.User
    ) -> None:
        """
        give someone a few pats
        """

        if who == ctx.author:
            titles: list[str] = [
                "u pat urself on the back... literally",
                "u try to pat ur own head, it  looks silly",
                "u give urself a little pat, awww",
                "u pat urself because no one else will",
            ]
        else:
            titles = [
                "{initiator} gives {target} a gentle pat",
                "{initiator} pats {target} on the head affectionately",
                "{initiator} bestows a soft pat upon {target}",
                "{initiator} pats {target} like a good puppy",
                "{initiator} pats {target} professionally",
                "{initiator} pats{target} while saying 'WHOS A GOOD BOY??'",
            ]

        if who == ctx.bot.user:
            footers: list[str] | None = [
                "pp bot appreciates the pats",
                "pats for pp bot are always welcome",
                "pp bot pats you back!",
                "so kind to pat pp bot",
            ]
        else:
            footers = None

        await self.send_animu_embed(
            ctx,
            "pat",
            ctx.author,
            who,
            titles,
            footers,
        )

    @commands.command(
        "hug",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="who",
                    type=discord.ApplicationCommandOptionType.user,
                    description="who needs a warm hug?",
                )
            ]
        ),
    )
    @commands.is_slash_command()
    async def hug_command(
        self, ctx: commands.SlashContext[utils.Bot], who: discord.Member | discord.User
    ) -> None:
        """
        give someone a hug
        """

        if who == ctx.author:
            titles: list[str] = [
                "u hug urself... self-love is important!",
                "u give urself a big ol' hug",
                "u wrap ur arms around urself, aww",
                "u hug urself because why not?",
                "hugging urself is sad as shit ngl",
            ]
        else:
            titles = [
                "{initiator} gives {target} a warm hug",
                "{initiator} wraps {target} in a tight embrace",
                "{initiator} hugs {target} tightly",
                "{initiator} pulls {target} into a loving hug",
                "{initiator} squishes {target} aggressively",
            ]

        if who == ctx.bot.user:
            footers: list[str] | None = [
                "pp bot loves hugs!",
                "hugs for pp bot are the best",
                "pp bot hugs you back!",
                "so kind to hug pp bot",
            ]
        else:
            footers = None

        await self.send_animu_embed(
            ctx,
            "hug",
            ctx.author,
            who,
            titles,
            footers,
        )

    @commands.command(
        "wink",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    name="who",
                    type=discord.ApplicationCommandOptionType.user,
                    description="who gets a sneaky wink?",
                )
            ]
        ),
    )
    @commands.is_slash_command()
    async def wink_command(
        self, ctx: commands.SlashContext[utils.Bot], who: discord.Member | discord.User
    ) -> None:
        """
        wink at someone
        """

        if who == ctx.author:
            titles: list[str] = [
                "u wink at urself and pull a muscle. smooth.",
                "u wink so hard both eyes close. nice one.",
                "u try to wink but just look like ur having a seizure",
                "u wink at urself. that's not how winking works.",
                "congrats, u just winked at ur own reflection. ur legally required to marry it now.",
            ]
        else:
            titles = [
                "{initiator} winks at {target} so hard they lose balance and fall over",
                "{initiator} gives {target} a wink",
                "{initiator} winks at {target} but accidentally uses both eyes",
                "{initiator} winks at {target} aggressively",
                "{initiator} winks at {target} in a weird way",
            ]

        if who == ctx.bot.user:
            footers: list[str] | None = [
                "pp bot winks back",
                "pp bot files a restraining order against u",
            ]
        else:
            footers = None

        await self.send_animu_embed(
            ctx,
            "wink",
            ctx.author,
            who,
            titles,
            footers,
        )

    @commands.command(
        "facepalm",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def facepalm_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        when something is so stupid u gotta facepalm
        """

        titles: list[str] = [
            "{initiator} facepalms so hard they leave a handprint",
            "{initiator} slaps their forehead in pure disappointment",
            "{initiator} facepalms into another dimension",
            "{initiator} asks god why",
            "{initiator} has lost all faith in humanity",
            "{initiator} facepalms so aggressively they give themselves a concussion",
            "{initiator} lowkey just ends it all",
        ]

        await self.send_animu_embed(
            ctx,
            "face-palm",
            ctx.author,
            None,
            titles,
            None,
        )


async def setup(bot: utils.Bot):
    await bot.add_cog(AnimuCommandsCog(bot))
