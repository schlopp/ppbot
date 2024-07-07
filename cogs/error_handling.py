import io
import random
import traceback
from collections.abc import Callable
from datetime import timedelta
from typing import Any, TypeVar

import aiohttp
import discord
from discord.ext import commands, vbu

from . import utils


_T_CommandError = TypeVar("_T_CommandError", bound=commands.CommandError)
CommandErrorResponseFactory = Callable[
    [vbu.Context[discord.Guild | None], _T_CommandError], utils.Embed
]


class ErrorHandler(vbu.Cog):

    command_error_responses: dict[
        type[commands.CommandError],
        CommandErrorResponseFactory,
    ] = {}

    @classmethod
    def command_error_response(cls, *error_types: type[_T_CommandError]):
        def deco(
            func: Callable[
                [vbu.Context[discord.Guild | None], _T_CommandError], utils.Embed
            ]
        ):
            for error_type in error_types:
                cls.command_error_responses[error_type] = func
            return func

        return deco

    @staticmethod
    def error_embed_factory(ctx: commands.Context) -> utils.Embed:
        embed = utils.Embed(color=utils.RED)
        embed.title = random.choice(
            [
                f"Oopsie {ctx.author.display_name},",
                "Oopsie, I'm just a girl🎀",
                "Nuh uh",
                "Error!!!!!",
                "No.",
                "System overload.",
                "You fucked up",
                "Something went wrong :(",
                "Does anyone read these error titles?",
            ]
        )

        return embed

    LEGACY_COMMAND_ERROR_RESPONSES = (
        (
            vbu.errors.MissingRequiredArgumentString,
            lambda ctx, error: (
                "You're missing `{parameter_name}`, which is required for this command."
            ).format(parameter_name=error.param),
        ),
        (
            commands.MissingRequiredArgument,
            lambda ctx, error: (
                "You're missing `{parameter_name}`, which is required for this command."
            ).format(parameter_name=error.param.name),
        ),
        (
            (
                commands.UnexpectedQuoteError,
                commands.InvalidEndOfQuotedStringError,
                commands.ExpectedClosingQuoteError,
            ),
            lambda ctx, error: (
                "The quotes in your message have been done incorrectly."
            ),
        ),
        (
            commands.CommandOnCooldown,
            lambda ctx, error: (
                "You can use this command again in {timestamp}."
            ).format(
                timestamp=discord.utils.format_dt(
                    discord.utils.utcnow() + timedelta(seconds=error.retry_after),
                    style="R",
                )
            ),
        ),
        (
            vbu.errors.BotNotReady,
            lambda ctx, error: (
                "The bot isn't ready to start processing that command yet - please wait."
            ),
        ),
        (
            commands.NSFWChannelRequired,
            lambda ctx, error: (
                "You can only run this command in channels set as NSFW."
            ),
        ),
        (
            commands.IsNotSlashCommand,
            lambda ctx, error: {
                True: ("This command can only be run as a slash command."),
                False: (
                    "This command can only be run as a slash command. Please re-invite the bot to add slash commands to your server."
                ),
            }[error.missing_scope],
        ),
        (
            commands.DisabledCommand,
            lambda ctx, error: ("This command has been disabled."),
        ),
        (
            vbu.errors.NotBotSupport,
            lambda ctx, error: (
                "You need to be part of the bot's support team to be able to run this command."
            ),
        ),
        (
            commands.MissingAnyRole,
            lambda ctx, error: (
                "You need to have at least one of {roles} to be able to run this command."
            ).format(roles=", ".join(f"`{i.mention}`" for i in error.missing_roles)),
        ),
        (
            commands.BotMissingAnyRole,
            lambda ctx, error: (
                "I need to have one of the {roles} roles for you to be able to run this command."
            ).format(roles=", ".join(f"`{i.mention}`" for i in error.missing_roles)),
        ),
        (
            commands.MissingRole,
            lambda ctx, error: (
                "You need to have the `{role}` role to be able to run this command."
            ).format(role=error.missing_role),
        ),
        (
            commands.BotMissingRole,
            lambda ctx, error: (
                "I need to have the `{role}` role for you to be able to run this command."
            ).format(role=error.missing_role),
        ),
        (
            commands.MissingPermissions,
            lambda ctx, error: (
                "You need the `{permission}` permission to run this command."
            ).format(permission=error.missing_permissions[0].replace("_", " ")),
        ),
        (
            commands.BotMissingPermissions,
            lambda ctx, error: (
                "I need the `{permission}` permission for me to be able to run this command."
            ).format(permission=error.missing_permissions[0].replace("_", " ")),
        ),
        (
            commands.NoPrivateMessage,
            lambda ctx, error: ("This command can't be run in DMs."),
        ),
        (
            commands.PrivateMessageOnly,
            lambda ctx, error: ("This command can only be run in DMs."),
        ),
        (
            commands.NotOwner,
            lambda ctx, error: (
                "You need to be registered as an owner to run this command."
            ),
        ),
        (
            commands.MessageNotFound,
            lambda ctx, error: (
                "I couldn't convert `{argument}` into a message."
            ).format(argument=error.argument),
        ),
        (
            commands.MemberNotFound,
            lambda ctx, error: (
                "I couldn't convert `{argument}` into a guild member."
            ).format(argument=error.argument),
        ),
        (
            commands.UserNotFound,
            lambda ctx, error: ("I couldn't convert `{argument}` into a user.").format(
                argument=error.argument
            ),
        ),
        (
            commands.ChannelNotFound,
            lambda ctx, error: (
                "I couldn't convert `{argument}` into a channel."
            ).format(argument=error.argument),
        ),
        (
            commands.ChannelNotReadable,
            lambda ctx, error: ("I can't read messages in <#{id}>.").format(
                id=error.argument.id
            ),
        ),
        (
            commands.BadColourArgument,
            lambda ctx, error: (
                "I couldn't convert `{argument}` into a colour."
            ).format(argument=error.argument),
        ),
        (
            commands.RoleNotFound,
            lambda ctx, error: ("I couldn't convert `{argument}` into a role.").format(
                argument=error.argument
            ),
        ),
        (
            commands.BadInviteArgument,
            lambda ctx, error: (
                "I couldn't convert `{argument}` into an invite."
            ).format(argument=error.argument),
        ),
        (
            (commands.EmojiNotFound, commands.PartialEmojiConversionFailure),
            lambda ctx, error: (
                "I couldn't convert `{argument}` into an emoji."
            ).format(argument=error.argument),
        ),
        (
            commands.BadBoolArgument,
            lambda ctx, error: (
                "I couldn't convert `{argument}` into a boolean."
            ).format(argument=error.argument),
        ),
        (
            commands.BadUnionArgument,
            lambda ctx, error: (
                "I couldn't convert your provided `{parameter_name}`."
            ).format(parameter_name=error.param.name),
        ),
        (
            commands.BadArgument,
            lambda ctx, error: str(error).format(ctx=ctx, error=error),
        ),
        (
            commands.MaxConcurrencyReached,
            lambda ctx, error: ("You can't run this command right now."),
        ),
        (
            commands.TooManyArguments,
            lambda ctx, error: ("You gave too many arguments to this command."),
        ),
        (discord.NotFound, lambda ctx, error: str(error).format(ctx=ctx, error=error)),
        (
            commands.CheckFailure,
            lambda ctx, error: str(error).format(ctx=ctx, error=error),
        ),
        (
            discord.Forbidden,
            lambda ctx, error: ("Discord is saying I'm unable to perform that action."),
        ),
        (
            (discord.HTTPException, aiohttp.ClientOSError),
            lambda ctx, error: (
                "Either I or Discord messed up running this command. Please try again later."
            ),
        ),
        # Disabled because they're base classes for the subclasses above
        # (commands.CommandError, lambda ctx, error: ""),
        # (commands.CheckFailure, lambda ctx, error: ""),
        # (commands.CheckAnyFailure, lambda ctx, error: ""),
        # (commands.CommandInvokeError, lambda ctx, error: ""),
        # (commands.UserInputError, lambda ctx, error: ""),
        # (commands.ConversionError, lambda ctx, error: ""),
        # (commands.ArgumentParsingError, lambda ctx, error: ""),
        # Disabled because they all refer to extension and command loading
        # (commands.ExtensionError, lambda ctx, error: ""),
        # (commands.ExtensionAlreadyLoaded, lambda ctx, error: ""),
        # (commands.ExtensionNotLoaded, lambda ctx, error: ""),
        # (commands.NoEntryPointError, lambda ctx, error: ""),
        # (commands.ExtensionFailed, lambda ctx, error: ""),
        # (commands.ExtensionNotFound, lambda ctx, error: ""),
        # (commands.CommandRegistrationError, lambda ctx, error: ""),
    )

    async def send_embed_to_ctx_or_author(
        self, ctx: vbu.Context, embed: discord.Embed
    ) -> discord.Message | None:
        kwargs: dict[str, Any] = {
            "embed": embed,
            "allowed_mentions": discord.AllowedMentions.none(),
        }
        if isinstance(ctx, commands.SlashContext) and self.bot.config.get(
            "ephemeral_error_messages", True
        ):
            kwargs.update({"ephemeral": True})
        try:
            return await ctx.send(**kwargs)
        except discord.Forbidden:
            try:
                return await ctx.author.send(**kwargs)
            except discord.Forbidden:
                pass
        except discord.NotFound:
            pass
        return None

    async def send_to_ctx_or_author(
        self, ctx: vbu.Context, text: str, author_text: str | None = None
    ) -> discord.Message | None:
        """
        Tries to send the given text to ctx, but failing that, tries to send it to the author
        instead. If it fails that too, it just stays silent.
        """

        embed = self.error_embed_factory(ctx)
        embed.description = text
        embed.add_tip()

        kwargs: dict[str, Any] = {
            "embed": embed,
            "allowed_mentions": discord.AllowedMentions.none(),
        }
        if isinstance(ctx, commands.SlashContext) and self.bot.config.get(
            "ephemeral_error_messages", True
        ):
            kwargs.update({"ephemeral": True})
        try:
            return await ctx.send(**kwargs)
        except discord.Forbidden:
            embed.description = text or author_text
            try:
                return await ctx.author.send(**kwargs)
            except discord.Forbidden:
                pass
        except discord.NotFound:
            pass
        return None

    @vbu.Cog.listener()
    async def on_command_error(self, ctx: vbu.Context, error: commands.CommandError):
        """
        Global error handler for all the commands around wew.
        """

        # Set up some errors that are just straight up ignored
        ignored_errors = (
            commands.CommandNotFound,
            vbu.errors.InvokedMetaCommand,
        )
        if isinstance(error, ignored_errors):
            return
        self.logger.info(f"Hit error in command {ctx.command} - {error}")

        # See what we've got to deal with
        setattr(
            ctx, "original_author_id", getattr(ctx, "original_author_id", ctx.author.id)
        )

        # Set up some errors that the owners are able to bypass
        owner_reinvoke_errors = (
            commands.MissingRole,
            commands.MissingAnyRole,
            commands.MissingPermissions,
            commands.CommandOnCooldown,
            commands.DisabledCommand,
            commands.CheckFailure,
            vbu.errors.IsNotUpgradeChatSubscriber,
            vbu.errors.IsNotVoter,
            vbu.errors.NotBotSupport,
        )
        if (
            isinstance(error, owner_reinvoke_errors)
            and ctx.original_author_id in self.bot.owner_ids
        ):
            if not self.bot.config.get("owners_ignore_command_errors", True):
                pass
            elif not self.bot.config.get(
                "owners_ignore_check_failures", True
            ) and isinstance(error, commands.CheckFailure):
                pass
            else:
                return await ctx.reinvoke()

        # See if the command itself has an error handler AND it isn't a locally handlled arg
        # if hasattr(ctx.command, "on_error") and not isinstance(ctx.command, commands.command):
        if hasattr(ctx.command, "on_error"):
            return

        # See if it's in our list of common outputs
        output = None
        error_found = False

        for error_type, function in self.command_error_responses.items():
            if isinstance(error, error_type):
                error_found = True
                output = function(ctx, error)
                break

        # Send a message based on the output
        if output is not None:
            return await self.send_embed_to_ctx_or_author(ctx, output)

        for error_types, function in self.LEGACY_COMMAND_ERROR_RESPONSES:
            if isinstance(error, error_types):
                error_found = True
                output = function(ctx, error)
                break

        # Send a message based on the output
        if output:
            return await self.send_to_ctx_or_author(ctx, output)

        # Make sure not to send an error if it's "handled"
        if error_found:
            return

        # The output isn't a common output -- send them a plain error response
        try:
            await ctx.send(
                f"`{str(error).strip()}`",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.NotFound):
            pass

        # Ping unhandled errors to the owners and to the event webhook
        error_string = "".join(
            traceback.format_exception(None, error, error.__traceback__)
        )
        file_handle = io.StringIO(error_string + "\n")
        guild_id = ctx.guild.id if ctx.guild else None
        error_text = (
            f"Error `{error}` encountered.\nGuild `{guild_id}`, channel `{ctx.channel.id}`, "
            f"user `{ctx.author.id}`\n```\n{ctx.message.content if ctx.message else '[No message content]'}\n```"
        )

        # DM to owners
        if self.bot.config.get("dm_uncaught_errors", False):
            for owner_id in self.bot.owner_ids:
                owner = self.bot.get_user(owner_id)
                if not owner and (
                    self.bot.shard_count is None or self.bot.shard_count < 50
                ):
                    owner = await self.bot.fetch_user(owner_id)
                elif not owner:
                    continue
                file_handle.seek(0)
                await owner.send(
                    error_text, file=discord.File(file_handle, filename="error_log.py")
                )

        # Ping to the webook
        event_webhook: discord.Webhook | None = self.bot.get_event_webhook(
            "unhandled_error"
        )
        try:
            avatar_url = str(self.bot.user.display_avatar.url)
        except Exception:
            avatar_url = None
        if event_webhook:
            file_handle.seek(0)
            try:
                file = discord.File(file_handle, filename="error_log.py")
                await event_webhook.send(
                    error_text,
                    file=file,
                    username=f"{self.bot.user.name} - Error",
                    avatar_url=avatar_url,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException as e:
                self.logger.error(
                    f"Failed to send webhook for event unhandled_error - {e}"
                )

        # And throw it into the console
        logger = getattr(getattr(ctx, "cog", self), "logger", self.logger)
        for line in error_string.strip().split("\n"):
            logger.error(line)


@ErrorHandler.command_error_response(commands.CommandOnCooldown)
def handle_command_error(
    ctx: vbu.Context, error: commands.CommandOnCooldown
) -> utils.Embed:
    embed = ErrorHandler.error_embed_factory(ctx)
    embed.title = random.choice(
        [
            "SLOW THE FUCK DOWN",
            "calm down lil bro",
            "not so fast",
            "coooooooldooooown",
            "too fast so sad",
            "womp womp",
            "bro, slow down",
        ]
    )

    if error.cooldown.rate == 1:
        cooldown = utils.format_time(error.cooldown.per)
    else:
        cooldown = "{rate} times per {per}".format(
            rate=utils.format_int(error.cooldown.rate),
            per=utils.format_time(error.cooldown.per),
        )

    if ctx.command is None:
        cooldown_label = "Cooldown"
    else:
        cooldown_label = f"{utils.format_slash_command(ctx.command.name)} cooldown"

    embed.description = (
        "You can use this command again in **{time_left}**"
        "\n\n{cooldown_label}: `{cooldown}`"
    ).format(
        time_left=utils.format_time(error.retry_after, max_decimals=1),
        cooldown_label=cooldown_label,
        cooldown=cooldown,
    )

    return embed


async def setup(bot: vbu.Bot):
    x = ErrorHandler(bot)
    await bot.add_cog(x)
