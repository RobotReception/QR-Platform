"""
Distributed rate limiter with Redis backend and in-memory fallback.

Uses a sliding-window algorithm (Redis sorted sets) so the same limits hold
across multiple API processes/replicas. If Redis is unreachable the limiter
degrades gracefully to a per-process in-memory window — the API keeps serving
rather than failing closed, and a warning is logged.

Production deployments MUST run Redis (REDIS_URL) so limits are enforced
fleet-wide; the in-memory path is a dev/outage safety net only.
"""
import logging
import time
from collections import defaultdict

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    import redis.asyncio as aioredis
except Exception:  # redis not installed
    aioredis = None


class RateLimiter:
    """Sliding-window rate limiter. Redis-backed when available, else in-memory."""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or settings.redis_url
        self._redis = None
        self._redis_ok = False
        self._mem: dict[str, list[float]] = defaultdict(list)
        if aioredis and self._redis_url:
            try:
                self._redis = aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                self._redis_ok = True
            except Exception as e:
                logger.warning("Rate limiter: Redis init failed, using in-memory fallback: %s", e)
                self._redis = None

    async def hit(self, key: str, limit: int, window: float) -> bool:
        """Record a request for `key` and return True if it is within `limit`
        over the trailing `window` seconds."""
        now = time.time()
        if self._redis is not None and self._redis_ok:
            try:
                return await self._hit_redis(key, limit, window, now)
            except Exception as e:
                # First failure: warn and fall back for this and subsequent calls.
                if self._redis_ok:
                    logger.warning("Rate limiter: Redis unavailable, falling back to in-memory: %s", e)
                self._redis_ok = False
        return self._hit_memory(key, limit, window, now)

    async def _hit_redis(self, key: str, limit: int, window: float, now: float) -> bool:
        redis_key = f"rl:{key}:{int(window)}"
        cutoff = now - window
        member = f"{now:.6f}"
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, cutoff)
        pipe.zadd(redis_key, {member: now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, int(window) + 1)
        results = await pipe.execute()
        count = results[2]
        return count <= limit

    def _hit_memory(self, key: str, limit: int, window: float, now: float) -> bool:
        bucket = [t for t in self._mem[key] if now - t < window]
        bucket.append(now)
        self._mem[key] = bucket
        return len(bucket) <= limit

    @property
    def backend(self) -> str:
        return "redis" if (self._redis is not None and self._redis_ok) else "memory"


# Shared singleton used by middleware.
rate_limiter = RateLimiter()
