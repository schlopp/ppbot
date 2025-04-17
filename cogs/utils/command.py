from __future__ import annotations
import time
from datetime import timezone
from enum import Enum
from typing import Any, cast, Callable, Coroutine

import discord
from discord.ext import commands, vbu

from . import Bot


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
        ctx: commands.Context[Bot],
        identifier: discord.Message | discord.Interaction,
    ) -> Any:
        ctx.command = cast(Command, ctx.command)
        if (
            self._type == commands.BucketType.default
        ):  # pyright: ignore [reportUnnecessaryComparison]
            return f"cooldowns:{ctx.command.name}:default"
        return f"cooldowns:{ctx.command.name}:{self._type(identifier)}"

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


class Command(commands.Command):
    _buckets: RedisCooldownMapping

    def __init__(
        self,
        func,
        *,
        category: CommandCategory = CommandCategory.OTHER,
        cooldown_factory: CooldownFactory | None = None,
        **kwargs,
    ):
        super().__init__(func, **kwargs)
        self.category = category

        try:
            self._cooldown_factory = cast(
                CooldownFactory | None, func.__commands_cooldown_factory
            )
        except AttributeError:
            self._cooldown_factory = cooldown_factory

        self._buckets = RedisCooldownMapping(
            self._buckets._cooldown, self._buckets._type
        )

    async def _get_buckets(self, ctx: commands.Context[Bot]) -> RedisCooldownMapping:
        if self._cooldown_factory is not None:
            cooldown, bucket_type = await self._cooldown_factory(ctx)
            print(cooldown, bucket_type)
            return RedisCooldownMapping(cooldown, bucket_type)
        return self._buckets

    async def _async_prepare_cooldowns(self, ctx: commands.Context[Bot]) -> None:
        assert isinstance(ctx.command, Command)
        buckets = await self._get_buckets(ctx)
        if buckets.valid:
            dt = (ctx.message.edited_at or ctx.message.created_at) if ctx.message else discord.utils.snowflake_time(ctx.interaction.id)  # type: ignore
            current = dt.replace(tzinfo=timezone.utc).timestamp()
            cooldown, retry_after = await buckets.redis_update_rate_limit(
                buckets.redis_bucket_key(ctx, buckets.get_message(ctx)),
                current,
            )
            if retry_after:
                raise commands.CommandOnCooldown(cooldown, retry_after, buckets.type)  # type: ignore

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
                    buckets.redis_bucket_key(ctx, buckets.get_message(ctx)),
                    current,
                )
            )[0] == 0

    def reset_cooldown(self, *_, **_1):
        raise NotImplementedError("Use async_reset_cooldown instead.")

    async def async_reset_cooldown(self, ctx: commands.Context[Bot]) -> None:
        buckets = await self._get_buckets(ctx)
        if buckets.valid:
            await buckets.redis_reset(
                buckets.redis_bucket_key(ctx, buckets.get_message(ctx))
            )

    def get_cooldown_retry_after(self, *_, **_1):
        raise NotImplementedError("Use async_get_cooldown_retry_after instead.")

    async def async_get_cooldown_retry_after(self, ctx: commands.Context[Bot]):
        buckets = await self._get_buckets(ctx)
        if buckets.valid:
            dt = (ctx.message.edited_at or ctx.message.created_at) if ctx.message else discord.utils.snowflake_time(ctx.interaction.id)  # type: ignore
            current = dt.replace(tzinfo=timezone.utc).timestamp()
            return await buckets.redis_get_retry_after(
                buckets.redis_bucket_key(ctx, buckets.get_message(ctx)),
                current,
            )

        return 0.0
