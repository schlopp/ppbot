import asyncio
import time
import random
from datetime import timedelta

import discord
from discord.ext import vbu

from . import utils


class VotingEventsCog(vbu.Cog[utils.Bot]):
    MIN_VOTE_GROWTH = 90
    MAX_VOTE_GROWTH = 110

    def __init__(self, bot: utils.Bot, logger_name: str | None = None):
        super().__init__(bot, logger_name)

    def vote_acknowledgement_component_factory(self) -> discord.ui.MessageComponents:
        return discord.ui.MessageComponents(
            discord.ui.ActionRow(
                discord.ui.Button(
                    label="Remind me to vote again!",
                    custom_id=f"DM_VOTE_REMINDER",
                    style=discord.ButtonStyle.green,
                )
            )
        )

    async def _send_reminder(
        self,
        user: discord.User | discord.Member,
        *,
        bot_down: bool = False,
    ) -> None:
        self.logger.info(f"Sending reminder to {user} ({user.id})")
        dm_channel = user.dm_channel or await user.create_dm()

        embed = utils.Embed()
        embed.color = utils.PINK

        embed.title = random.choice(
            [
                "BEEP BEEP BEEP VOTE NOW!!!",
                "wakey wakey its voting time",
                "you can vote again !!",
            ]
        )

        embed.description = (
            f"[**Vote now**]({utils.VOTE_URL}) to get your **{utils.BoostType.VOTE.percentage}%**"
            f" voting boost back!"
        )

        if bot_down:
            embed.set_footer(
                text="This notification is late because the bot was down earlier :("
            )

        await dm_channel.send(embed=embed)

    def _schedule_reminder(
        self,
        user: discord.User | discord.Member,
        timestamp: float,
        *,
        bot_down: bool = False,
    ) -> None:
        self.logger.info(
            f"Scheduling reminder for {user} ({user.id}) at {timestamp} (UNIX)"
        )

        async def reminder() -> None:
            now = time.time()
            late = timestamp < now

            if not late:
                await asyncio.sleep(timestamp - now)

            async with vbu.Redis() as redis:
                await redis.delete(f"reminders:voting:{user.id}")

            await self._send_reminder(user, bot_down=bot_down)

        self.bot.loop.create_task(reminder())

    @vbu.Cog.listener("on_ready")
    async def reschedule_existing_reminders(self) -> None:
        async with vbu.Redis() as redis:
            async for reminder_key in redis.pool.iscan(match="reminders:voting:*"):
                user_id = int(reminder_key.split(b":")[-1])
                user = await self.bot.fetch_user(user_id)

                reminder_timestamp_data = await redis.get(reminder_key)
                assert reminder_timestamp_data

                reminder_timestamp = int(reminder_timestamp_data)
                self._schedule_reminder(user, reminder_timestamp, bot_down=True)

    @vbu.Cog.listener("on_component_interaction")
    async def handle_vote_reminder_button_interaction(
        self, component_interaction: discord.ComponentInteraction
    ) -> None:
        if component_interaction.custom_id.split("_", maxsplit=1)[0] != "DM":
            return

        _, action = component_interaction.custom_id.split("_", maxsplit=1)

        if action != "VOTE_REMINDER":
            return

        user = component_interaction.user

        async with vbu.Redis() as redis:
            redis_key = f"pending-interactions:vote-reminder:{user.id}"
            vote_reminder_data = await redis.get(redis_key)

            if vote_reminder_data is None:
                raise Exception(
                    f"No registered pending interaction for vote reminder on {user.id},"
                    " yet component interaction was received."
                )

            await redis.delete(redis_key)

            vote_timestamp = int(vote_reminder_data.split(":")[0])
            next_vote_timestamp = vote_timestamp + timedelta(hours=12).seconds
            self._schedule_reminder(user, next_vote_timestamp)

            await redis.set(f"reminders:voting:{user.id}", str(next_vote_timestamp))

            components = self.vote_acknowledgement_component_factory()
            components.disable_components()
            await component_interaction.response.edit_message(components=components)

            if next_vote_timestamp > time.time():
                await component_interaction.followup.send(
                    f"You will be reminded to vote at <t:{next_vote_timestamp}:t>!"
                    " Thank u so much for ur support :)",
                    ephemeral=True,
                )

    @vbu.Cog.listener("on_vote")
    async def acknowledge_vote_event(self, user: discord.User) -> None:
        vote_timestamp = int(time.time())
        dm_channel = user.dm_channel or await user.create_dm()

        async with (
            utils.DatabaseWrapper() as db,
            utils.DatabaseTimeoutManager.notify(
                user.id, "We're still processing your vote."
            ),
        ):
            transaction = db.conn.transaction()
            await transaction.start()

            # Very generous timeout, just in case someone votes while they're busy
            # (e.g. using casino)
            timeout = 60 * 2

            try:
                pp = await utils.Pp.fetch_from_user(
                    db.conn, user.id, edit=True, timeout=timeout
                )
            except utils.DatabaseTimeout as error:
                await transaction.rollback()
                transaction = db.conn.transaction()
                await transaction.start()

                try:
                    # Even more generous timeout
                    timeout = 60 * 10

                    await dm_channel.send(
                        (
                            "We can't give you your voting gift <:ppMalding:902894208795435031>"
                            " {reason} We'll try to send your reward again in"
                            " {duration} <:ppHappy:902894208703156257>"
                        ).format(
                            reason=error.reason,
                            duration=utils.format_time(timeout),
                        )
                    )

                    try:
                        pp = await utils.Pp.fetch_from_user(
                            db.conn, user.id, edit=True, timeout=timeout
                        )
                    except utils.DatabaseTimeout as error:
                        try:
                            await dm_channel.send(
                                (
                                    "It's been {duration} and we still can't give you your"
                                    " voting gift. {reason}"
                                    "\nSucks to suck, atleast you get the **{boost_percentage}%"
                                    " BOOST** :)"
                                ).format(
                                    duration=utils.format_time(timeout),
                                    reason=error.reason,
                                    boost_percentage=utils.BoostType.VOTE.percentage,
                                )
                            )
                        except discord.HTTPException as error:
                            self.logger.info(
                                "Could'nt DM vote and 2nd database timeout acknowledgement to user"
                                f" {user} ({user.id}): {error}"
                            )
                        await transaction.rollback()
                        return

                except discord.HTTPException as error:
                    self.logger.info(
                        "Could'nt DM vote and database timeout acknowledgement to user"
                        f" {user} ({user.id}): {error}"
                    )
                    await transaction.rollback()
                    return

                except:
                    await transaction.rollback()
                    raise

            # Emulate async-with block, which we can't use due to the possibility
            # of multiple transactions being necessary (see code above)
            try:
                pp.grow_with_multipliers(
                    random.randint(self.MIN_VOTE_GROWTH, self.MAX_VOTE_GROWTH),
                    voted=await pp.has_voted(),
                )
                await pp.update(db.conn)
            except:
                await transaction.rollback()
            else:
                await transaction.commit()

        embed = utils.Embed()
        embed.color = utils.PINK
        embed.title = random.choice(
            [
                "THANKS 4 VOTING",
                "TY FOR THE VOTE",
                "I LOVE VOTERS I LOVE VOTERS I LOVE VOTERS",
                "YOU VOTED? FUCK YEAH",
                "AUUUGGGHHHH I LOVE VOTERS",
                "THANK YOU FOR VOTING !!",
            ]
        )
        embed.description = (
            "Here's {reward} as a gift :))"
            "\nYou're also getting a **{boost_percentage}% BOOST** for the next 12 hours"
            " until you vote again <:ppHappy:902894208703156257>"
        ).format(
            reward=pp.format_growth(),
            boost_percentage=utils.BoostType.VOTE.percentage,
        )

        async with vbu.Redis() as redis:
            vote_reminder_key = f"pending-interactions:vote-reminder:{user.id}"
            vote_reminder_data = await redis.get(vote_reminder_key)

            # Disable reminder component of previous vote notification
            if vote_reminder_data is not None:
                message_id = int(vote_reminder_data.split(":")[1])
                message = dm_channel.get_partial_message(message_id)
                components = self.vote_acknowledgement_component_factory()
                components.disable_components()
                await message.edit(components=components)

            try:
                message = await dm_channel.send(
                    embed=embed,
                    components=self.vote_acknowledgement_component_factory(),
                )
            except discord.HTTPException as error:
                self.logger.info(
                    f"Could'nt DM vote acknowledgement to user {user} ({user.id}): {error}"
                )
                return
            await redis.set(
                f"pending-interactions:vote-reminder:{user.id}",
                f"{vote_timestamp}:{message.id}",
            )


async def setup(bot: utils.Bot):
    if not bot.shard_ids or 0 in bot.shard_ids:
        await bot.add_cog(VotingEventsCog(bot))
