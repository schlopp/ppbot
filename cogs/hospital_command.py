import random

from discord.ext import commands, vbu
from . import utils


class HospitalCommandCog(vbu.Cog[utils.Bot]):
    MIN_SIZE = 50
    REWARD_RANGE = range(25, MIN_SIZE + 1)
    SUCCESS_RATE = 0.8

    @commands.command(
        "hospital",
        utils.Command,
        aliases=["h"],
        category=utils.CommandCategory.GROWING_PP,
        application_command_meta=commands.ApplicationCommandMeta(),
    )
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.is_slash_command()
    async def hospital_command(self, ctx: commands.SlashContext[utils.Bot]) -> None:
        """
        Take a risky surgery that can increase your pp size
        """
        async with (
            utils.DatabaseWrapper() as db,
            db.conn.transaction(),
            utils.DatabaseTimeoutManager.notify(
                ctx.author.id, "You're still busy with the hospital command!"
            ),
        ):
            pp = await utils.Pp.fetch_from_user(db.conn, ctx.author.id, edit=True)

            voted = await pp.has_voted()
            multiplier = pp.get_full_multiplier(voted=voted)[0]

            min_size = self.MIN_SIZE * multiplier

            if pp.size.value < min_size:
                assert isinstance(ctx.command, utils.Command)
                await ctx.command.async_reset_cooldown(ctx)
                raise commands.CheckFailure(
                    f"Your pp isn't big enough! You need at least **{utils.format_int(min_size)}"
                    " inches** to visit the hospital crodie"
                )

            embed = utils.Embed()
            embed.title = "HOSPITAL"
            embed.description = (
                f"{ctx.author.mention} goes to the hospital for some pp surgery..."
            )

            growth = random.choice(self.REWARD_RANGE) * multiplier

            # success!
            if random.random() < self.SUCCESS_RATE:
                pp.grow(growth)
                embed.color = utils.GREEN
                embed.add_field(
                    name="SUCCESSFUL",
                    value=(
                        "The operation was successful!"
                        f" Your pp gained {pp.format_growth()}!"
                        f" It is now {pp.format_growth(pp.size.value)}."
                    ),
                )

            # L moves
            else:
                pp.grow(-growth)
                embed.color = utils.RED
                embed.add_field(
                    name="FAILED",
                    value=(
                        "The operation failed."
                        f" Your pp snapped and you lost {pp.format_growth()} 😭"
                        f" It is now {pp.format_growth(pp.size.value)}."
                    ),
                )

            await pp.update(db.conn)

            embed.add_tip()

            await ctx.interaction.response.send_message(embed=embed)


async def setup(bot: utils.Bot):
    await bot.add_cog(HospitalCommandCog(bot))
