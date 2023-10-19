from __future__ import annotations
from datetime import timezone
import time
from typing import Any, cast
import discord
from discord.ext import commands, vbu
from . import Bot


class RedisCooldownMapping(commands.CooldownMapping):
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

        data = cast(str | None, await redis.get(key))

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


class Command(commands.Command):
    _buckets: RedisCooldownMapping

    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)
        self._buckets = RedisCooldownMapping(
            self._buckets._cooldown, self._buckets._type
        )

    async def _async_prepare_cooldowns(self, ctx: commands.Context[Bot]) -> None:
        assert isinstance(ctx.command, Command)
        if self._buckets.valid:
            dt = (ctx.message.edited_at or ctx.message.created_at) if ctx.message else discord.utils.snowflake_time(ctx.interaction.id)  # type: ignore
            current = dt.replace(tzinfo=timezone.utc).timestamp()
            cooldown, retry_after = await self._buckets.redis_update_rate_limit(
                self._buckets.redis_bucket_key(ctx, self._buckets.get_message(ctx)),
                current,
            )
            if retry_after:
                raise commands.CommandOnCooldown(cooldown, retry_after, self._buckets.type)  # type: ignore

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

    def is_on_cooldown(self, *_):
        raise NotImplementedError("Use async_is_on_cooldown instead.")

    async def async_is_on_cooldown(self, ctx: commands.Context[Bot]) -> bool:
        if not self._buckets.valid:
            return False
        dt = (ctx.message.edited_at or ctx.message.created_at) if ctx.message else discord.utils.snowflake_time(ctx.interaction.id)  # type: ignore
        current = dt.replace(tzinfo=timezone.utc).timestamp()
        async with vbu.Redis() as redis:
            return (
                await self._buckets.redis_get_bucket(
                    redis,
                    self._buckets.redis_bucket_key(ctx, self._buckets.get_message(ctx)),
                    current,
                )
            )[0] == 0

    def reset_cooldown(self, *_):
        raise NotImplementedError("Use async_reset_cooldown instead.")

    async def async_reset_cooldown(self, ctx: commands.Context[Bot]) -> None:
        if self._buckets.valid:
            await self._buckets.redis_reset(
                self._buckets.redis_bucket_key(ctx, self._buckets.get_message(ctx))
            )

    def get_cooldown_retry_after(self, *_):
        raise NotImplementedError("Use async_get_cooldown_retry_after instead.")

    async def async_get_cooldown_retry_after(self, ctx: commands.Context[Bot]):
        if self._buckets.valid:
            dt = (ctx.message.edited_at or ctx.message.created_at) if ctx.message else discord.utils.snowflake_time(ctx.interaction.id)  # type: ignore
            current = dt.replace(tzinfo=timezone.utc).timestamp()
            return await self._buckets.redis_get_retry_after(
                self._buckets.redis_bucket_key(ctx, self._buckets.get_message(ctx)),
                current,
            )

        return 0.0
