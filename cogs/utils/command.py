from __future__ import annotations
import time
from datetime import timezone
from enum import Enum
from typing import Any, cast, Callable, Coroutine, Self, TypedDict

import discord
from discord.ext import commands, vbu

from . import Bot, format_cooldown, VOTE_URL


type ExtendBucketType = commands.BucketType | Callable[
    [discord.Message | discord.Interaction], Any
]
type CooldownFactory = Callable[
    [commands.Context[Bot]],
    Coroutine[Any, Any, tuple[commands.Cooldown, ExtendBucketType]],
]


class RedisCooldownMapping(commands.CooldownMapping):

    def __init__(self, original: commands.Cooldown | None, type: ExtendBucketType):
        super().__init__(original, type)  # pyright: ignore[reportArgumentType]

    def redis_bucket_key(
        self,
        command: Command,
        identifier: discord.Message | discord.Interaction,
    ) -> Any:
        command = cast(Command, command)
        if (
            self._type == commands.BucketType.default
        ):  # pyright: ignore [reportUnnecessaryComparison]
            return f"cooldowns:{command.name}:default"
        return f"cooldowns:{command.name}:{self._type(identifier)}"

    async def redis_get_bucket(
        self, redis: vbu.Redis, key: str, current: float | None = None
    ) -> tuple[int, float]:
        """Returns `(tokens: int, window: float)`"""
        assert self._cooldown is not None

        if current is None:
            current = time.time()

        data = await redis.get(key)

        if data is None:
            tokens = self._cooldown.rate
            window = 0.0
        else:
            tokens_data, window_data = data.split(":")
            tokens = int(tokens_data)
            window = float(window_data)

        if current > window + self._cooldown.per:
            assert redis.conn is not None
            assert redis.pool is not None
            await redis.pool.delete(key)
            tokens = self._cooldown.rate

        return tokens, window

    async def redis_update_rate_limit(
        self, key: str, current: float | None = None
    ) -> tuple[commands.Cooldown, float | None]:
        """Returns `(cooldown: Cooldown, retry_after: float | None)`"""
        assert self._cooldown is not None
        if current is None:
            current = time.time()

        async with vbu.Redis() as redis:
            tokens, window = await self.redis_get_bucket(redis, key, current)

            if tokens == 0:
                return self._cooldown.copy(), self._cooldown.per - (current - window)

            if tokens == self._cooldown.rate:
                window = current

            tokens -= 1
            await redis.set(key, f"{tokens}:{window}")

        return self._cooldown.copy(), None

    async def redis_get_retry_after(
        self, key: str, current: float | None = None
    ) -> float:
        assert self._cooldown is not None
        if current is None:
            current = time.time()

        async with vbu.Redis() as redis:
            tokens, window = await self.redis_get_bucket(redis, key, current)

            if tokens == 0:
                return self._cooldown.per - (current - window)

        return 0.0

    async def redis_reset(self, key: str):
        assert self._cooldown is not None
        async with vbu.Redis() as redis:
            await redis.set(key, f"{self._cooldown._tokens}:0")


class CommandCategory(Enum):
    GETTING_STARTED = "getting started"
    STATS = "see ur stats"
    GROWING_PP = "growing ur pp"
    SHOP = "shop stuff"
    GAMBLING = "gambling time"
    FUN = "fun shit"
    OTHER = "other pp things"
    HELP = "help & info"


class CooldownTierInfoDict(TypedDict):
    default: commands.Cooldown
    voter: commands.Cooldown


class CommandOnCooldown(commands.CommandOnCooldown):
    def __init__(
        self,
        cooldown: commands.Cooldown,
        retry_after: float,
        type: commands.BucketType,
        *,
        tier_info: CooldownTierInfoDict | None = None,
    ) -> None:
        super().__init__(cooldown, retry_after, type)

        self.tier_info = tier_info

    @property
    def tier(self) -> str:
        if self.tier_info is None:
            return "default"

        for tier_name, tier_cooldown in self.tier_info.items():
            assert isinstance(tier_cooldown, commands.Cooldown)
            if (
                tier_cooldown.rate == self.cooldown.rate
                and tier_cooldown.per == self.cooldown.per
            ):
                return tier_name

        raise Exception(f"No tier matches cooldown {self.cooldown}")

    def format_tiers(self) -> str:
        if self.tier_info is None:
            return f"Cooldown: `{format_cooldown(self.cooldown)}`"

        tiers: list[str] = []
        for tier_name, tier_cooldown in self.tier_info.items():
            assert isinstance(tier_cooldown, commands.Cooldown)

            if tier_name == "voter":
                tier_name = f"[**{tier_name}**]({VOTE_URL})"

            tier = f"{tier_name} cooldown: `{format_cooldown(tier_cooldown)}`"

            if (
                tier_cooldown.rate == self.cooldown.rate
                and tier_cooldown.per == self.cooldown.per
            ):
                tier += " (This is you!)"

            tiers.append(tier)

        return "\n".join(tiers)


class Command(commands.Command):
    category: CommandCategory
    _cooldown_factory: CooldownFactory | None
    _buckets: RedisCooldownMapping

    def __init__(
        self,
        func,
        *,
        category: CommandCategory = CommandCategory.OTHER,
        cooldown_factory: CooldownFactory | None = None,
        cooldown_tier_info: CooldownTierInfoDict | None = None,
        **kwargs,
    ):
        super().__init__(func, **kwargs)
        self.category = category

        try:
            self._cooldown_factory = cast(
                CooldownFactory | None, func.__commands_cooldown_factory__
            )
        except AttributeError:
            self._cooldown_factory = cooldown_factory

        try:
            self._cooldown_tier_info = cast(
                CooldownTierInfoDict | None, func.__commands_cooldown_tier_info__
            )
        except AttributeError:
            self._cooldown_tier_info = cooldown_tier_info

        self._buckets = RedisCooldownMapping(
            self._buckets._cooldown, self._buckets._type
        )

    def _ensure_assignment_on_copy[CommandT: commands.Command](
        self: Self, other: CommandT
    ) -> CommandT:
        super()._ensure_assignment_on_copy(other)

        try:
            other._cooldown_factory = (  # pyright: ignore[reportAttributeAccessIssue]
                self._cooldown_factory
            )
        except AttributeError:
            pass

        return other

    async def _get_buckets(self, ctx: commands.Context[Bot]) -> RedisCooldownMapping:
        if self._cooldown_factory is not None:
            cooldown, bucket_type = await self._cooldown_factory(ctx)
            return RedisCooldownMapping(cooldown, bucket_type)
        return self._buckets

    async def _async_prepare_cooldowns(self, ctx: commands.Context[Bot]) -> None:
        assert isinstance(self, Command)
        buckets = await self._get_buckets(ctx)
        if buckets.valid:
            dt = (ctx.message.edited_at or ctx.message.created_at) if ctx.message else discord.utils.snowflake_time(ctx.interaction.id)  # type: ignore
            current = dt.replace(tzinfo=timezone.utc).timestamp()
            cooldown, retry_after = await buckets.redis_update_rate_limit(
                buckets.redis_bucket_key(self, buckets.get_message(ctx)),
                current,
            )
            if retry_after:
                raise CommandOnCooldown(cooldown, retry_after, buckets.type, tier_info=self._cooldown_tier_info)  # type: ignore

    async def _prepare_text(self, ctx: commands.Context[Bot]) -> None:
        ctx.command = self

        if not await self.can_run(ctx):
            raise commands.CheckFailure(
                f"The check functions for command {self.qualified_name} failed."
            )

        if self._max_concurrency is not None:
            # For this application, context can be duck-typed as a Message
            await self._max_concurrency.acquire(ctx)  # type: ignore

        try:
            if self.cooldown_after_parsing:
                await self._parse_arguments(ctx)
                await self._async_prepare_cooldowns(ctx)
            else:
                await self._async_prepare_cooldowns(ctx)
                await self._parse_arguments(ctx)

            await self.call_before_hooks(ctx)
        except:
            if self._max_concurrency is not None:
                await self._max_concurrency.release(ctx)  # type: ignore
            raise

    async def _prepare_slash(self, ctx: commands.SlashContext[Bot]) -> None:
        ctx.command = self

        if not await self.can_run(ctx):
            raise commands.CheckFailure(
                f"The check functions for command {self.qualified_name} failed."
            )

        if self._max_concurrency is not None:
            # For this application, context can be duck-typed as a Message
            await self._max_concurrency.acquire(ctx)  # type: ignore

        try:
            if self.cooldown_after_parsing:
                await self._parse_slash_arguments(ctx)
                await self._async_prepare_cooldowns(ctx)
            else:
                await self._async_prepare_cooldowns(ctx)
                await self._parse_slash_arguments(ctx)

            await self.call_before_hooks(ctx)
        except:
            if self._max_concurrency is not None:
                await self._max_concurrency.release(ctx)  # type: ignore
            raise

    def is_on_cooldown(self, *_, **_1):
        raise NotImplementedError("Use async_is_on_cooldown instead.")

    async def async_is_on_cooldown(self, ctx: commands.Context[Bot]) -> bool:
        buckets = await self._get_buckets(ctx)
        if not buckets.valid:
            return False
        dt = (ctx.message.edited_at or ctx.message.created_at) if ctx.message else discord.utils.snowflake_time(ctx.interaction.id)  # type: ignore
        current = dt.replace(tzinfo=timezone.utc).timestamp()
        async with vbu.Redis() as redis:
            return (
                await buckets.redis_get_bucket(
                    redis,
                    buckets.redis_bucket_key(self, buckets.get_message(ctx)),
                    current,
                )
            )[0] == 0

    def reset_cooldown(self, *_, **_1):
        raise NotImplementedError("Use async_reset_cooldown instead.")

    async def async_reset_cooldown(self, ctx: commands.Context[Bot]) -> None:
        buckets = await self._get_buckets(ctx)
        if buckets.valid:
            await buckets.redis_reset(
                buckets.redis_bucket_key(self, buckets.get_message(ctx))
            )

    def get_cooldown_retry_after(self, *_, **_1):
        raise NotImplementedError("Use async_get_cooldown_retry_after instead.")

    async def async_get_cooldown_retry_after(self, ctx: commands.Context[Bot]):
        buckets = await self._get_buckets(ctx)
        if buckets.valid:
            dt = (ctx.message.edited_at or ctx.message.created_at) if ctx.message else discord.utils.snowflake_time(ctx.interaction.id)  # type: ignore
            current = dt.replace(tzinfo=timezone.utc).timestamp()
            return await buckets.redis_get_retry_after(
                buckets.redis_bucket_key(self, buckets.get_message(ctx)),
                current,
            )

        return 0.0

    @classmethod
    def cooldown_factory[T](
        cls: type[Self],
        cooldown_factory: CooldownFactory,
        *,
        cooldown_tier_info: CooldownTierInfoDict | None = None,
    ) -> Callable[[T], T]:
        def decorator(
            func: Self | Callable[..., Coroutine[Any, Any, Any]],
        ) -> Self | Callable[..., Coroutine[Any, Any, Any]]:
            if isinstance(func, cls):
                func._cooldown_factory = cooldown_factory
                func._cooldown_tier_info = cooldown_tier_info
            else:
                func.__commands_cooldown_factory__ = (  # pyright: ignore[reportAttributeAccessIssue, reportFunctionMemberAccess]
                    cooldown_factory
                )
                func.__commands_cooldown_tier_info__ = (  # pyright: ignore[reportAttributeAccessIssue, reportFunctionMemberAccess]
                    cooldown_tier_info
                )
            return func

        return decorator  # type: ignore

    @classmethod
    def tiered_cooldown(
        cls: type[Self],
        *,
        default: commands.Cooldown | int,
        voter: commands.Cooldown | int,
    ):

        if isinstance(default, commands.Cooldown):
            default = default
        else:
            default = commands.Cooldown(1, default)

        if isinstance(voter, commands.Cooldown):
            voter = voter
        else:
            voter = commands.Cooldown(1, voter)

        cooldown_tier_info: CooldownTierInfoDict = {
            "default": default,
            "voter": voter,
        }

        async def cooldown_factory(
            ctx: commands.Context[Bot],
        ) -> tuple[commands.Cooldown, ExtendBucketType]:
            if await vbu.user_has_voted(ctx.author.id):
                tier = voter
            else:
                tier = default

            return tier, commands.BucketType.user

        return cls.cooldown_factory(
            cooldown_factory, cooldown_tier_info=cooldown_tier_info
        )
