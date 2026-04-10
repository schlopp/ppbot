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
]


class AnimuPayload(TypedDict):
    link: str
    type: str


class AnimuCommandsCog(vbu.Cog[utils.Bot]):
    BASE_URL = "https://api.some-random-api.com"
    animu_payload_cache: dict[AnimuLiterals, list[AnimuPayload]] = {}

    async def fetch_animu(
        self,
        animu: AnimuLiterals,
    ) -> AnimuPayload:
        async with aiohttp.ClientSession() as session:
            endpoint = f"{self.BASE_URL}/animu/{animu}"
            async with session.get(endpoint) as response:
                if response.status != 200:
                    self.logger.warning(
                        f"Received {response.status} from endpoint {endpoint}"
                    )
                    try:
                        payload = random.choice(self.animu_payload_cache[animu])
                    except:
                        raise Exception(
                            f"{endpoint} raised {response.status} and {animu!r} cache is empty"
                        )

                payload: AnimuPayload = await response.json()

                try:
                    self.animu_payload_cache[animu].append(payload)
                except KeyError:
                    self.animu_payload_cache[animu] = [payload]

                return payload

    async def send_animu_embed(
        self,
        ctx: commands.SlashContext[utils.Bot],
        animu: AnimuLiterals,
        initiator: discord.Member | discord.User,
        target: discord.Member | discord.User,
        titles: list[str],
        footers: list[str] | None = None,
    ) -> None:
        payload = await self.fetch_animu(animu)
        print(payload["link"])

        title = random.choice(titles)

        embed = utils.Embed()
        embed.set_image(url=payload["link"])
        embed.title = title.format(
            initiator=initiator.display_name, target=target.display_name
        )

        if footers is not None:
            embed.set_footer(text=random.choice(footers))

        await ctx.interaction.response.send_message(
            f"-# {title.format(initiator=initiator.mention, target=target.mention)}",
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


async def setup(bot: utils.Bot):
    await bot.add_cog(AnimuCommandsCog(bot))
