import asyncio
import random
import aiohttp
from typing import Literal, TypedDict

import discord
from discord.ext import commands, vbu

from . import utils


AnimalLiterals = Literal[
    "bird",
    "cat",
    "dog",
    "fox",
    "kangaroo",
    "koala",
    "panda",
    "raccoon",
    "red_panda",
]


class AnimalPayload(TypedDict):
    image: str
    fact: str


class AnimalCommandsCog(vbu.Cog[utils.Bot]):
    BASE_URL = "https://some-random-api.com"
    animal_payload_cache: dict[AnimalLiterals, list[AnimalPayload]] = {}

    async def fetch_animal(
        self,
        animal: AnimalLiterals,
    ) -> AnimalPayload:
        async with aiohttp.ClientSession() as session:
            endpoint = f"{self.BASE_URL}/animal/{animal}"
            async with session.get(endpoint) as response:
                if response.status != 200:
                    self.logger.warning(
                        f"Received {response.status} from endpoint {endpoint}"
                    )
                    payload = random.choice(self.animal_payload_cache[animal])

                payload: AnimalPayload = await response.json()

                try:
                    self.animal_payload_cache[animal].append(payload)
                except KeyError:
                    self.animal_payload_cache[animal] = [payload]

                return payload

    async def send_animal_embed(
        self,
        ctx: commands.SlashContext[utils.Bot],
        animal: AnimalLiterals,
        titles: list[str],
    ) -> None:
        payload = await self.fetch_animal(animal)

        embed = utils.Embed()
        embed.set_image(url=payload["image"])
        embed.title = random.choice(titles)
        embed.description = f"**Fun Fact:** {payload["fact"]}"

        await ctx.interaction.response.send_message(embed=embed)

    @commands.command(
        "bird",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def bird_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Bird pics for bird lovers
        """

        await self.send_animal_embed(
            ctx,
            "bird",
            [
                "birb pic for u!",
                "yes yes bird yes",
                "nice feathered lad",
                "round birb detected",
                "caw caw",
                "chirp chirp",
                "i require this birb",
                "This bird knows state secrets and must be watched.",
            ],
        )

    @commands.command(
        "cat",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def cat_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        mrowww mrow cute cat pictures
        """

        await self.send_animal_embed(
            ctx,
            "cat",
            [
                "cat pic for u!",
                "yes yes cat yes",
                "nice cat there",
                "chonky loaf",
                "mrow",
                "meow meow",
                "i must acquire this cat",
                "This cat runs an underground crime syndicate.",
            ],
        )

    @commands.command(
        "dog",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def dog_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Cute dog pics!!
        """

        await self.send_animal_embed(
            ctx,
            "dog",
            [
                "dog pic for u!",
                "yes yes dog yes",
                "nice dog there",
                "big ol pup",
                "rawr",
                "woof woof",
                "i want this dog",
                "This dog is wanted for manslaughter in 38 states.",
            ],
        )

    @commands.command(
        "fox",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def fox_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        BIG fox pictures. BIG
        """

        await self.send_animal_embed(
            ctx,
            "fox",
            [
                "fox pic for u!",
                "yes yes fox yes",
                "spicy woodland dog",
                "look at this orange rascal",
                "yip yip",
                "sneaky squeaky",
                "i would follow this fox into the forest, no questions asked",
                "This fox has three fake passports and zero regrets.",
            ],
        )

    @commands.command(
        "kangaroo",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def kangaroo_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Pics of big jumpy guys jumping around
        """

        await self.send_animal_embed(
            ctx,
            "kangaroo",
            [
                "kangaroo pic for u!",
                "yes yes roo yes",
                "pocket puppy",
                "look at this buff jumper",
                "boing boing",
                "thump thump",
                "i would let this kangaroo file my taxes",
                "This kangaroo is banned from five boxing rings and one Outback Steakhouse.",
            ],
        )

    @commands.command(
        "koala",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def koala_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Cool koala pics
        """

        await self.send_animal_embed(
            ctx,
            "koala",
            [
                "koala pic for u!",
                "yes yes koala yes",
                "eucalyptus gremlin",
                "look at this sleepy menace",
                "nom nom leaf",
                "climb climb nap",
                "i trust this koala with my deepest secrets",
                "This koala owes me $20 and pretends not to remember.",
            ],
        )

    @commands.command(
        "panda",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def panda_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        cute little (big) pandas
        """

        await self.send_animal_embed(
            ctx,
            "panda",
            [
                "panda pic for u!",
                "yes yes panda yes",
                "monochrome chaos bear",
                "look at this bamboo addict",
                "roll roll",
                "nom nom crunch",
                "i would commit tax fraud for this panda",
                "This panda has diplomatic immunity and no one knows why.",
            ],
        )

    @commands.command(
        "raccoon",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def raccoon_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        pics of little trash bears
        """

        await self.send_animal_embed(
            ctx,
            "raccoon",
            [
                "raccoon pic for u!",
                "yes yes raccoon yes",
                "tiny bandit",
                "look at this fuzzy dumpster wizard",
                "skitter skitter",
                "snatch and dash",
                "i would rob a convenience store with this raccoon",
                "This raccoon has five aliases and a court date in Nevada.",
            ],
        )

    @commands.command(
        "red-panda",
        utils.Command,
        category=utils.CommandCategory.FUN,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.is_slash_command()
    async def red_panda_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        pics of pandas.. but red!!
        """

        await self.send_animal_embed(
            ctx,
            "red_panda",
            [
                "red panda pic for u!",
                "yes yes red panda yes",
                "fire fox IRL",
                "look at this fluffy tree gremlin",
                "wiggle wiggle",
                "sniff sniff snoot",
                "i would protect this red panda with my life and legal team",
                "This red panda is on an international watchlist for being too adorable to trust.",
            ],
        )


async def setup(bot: utils.Bot):
    await bot.add_cog(AnimalCommandsCog(bot))
