import time
import uuid
import logging
from fastapi import HTTPException
from app.config import settings

try:
    import redis
    r = redis.from_url(settings.redis_url, decode_responses=True)
except ImportError:
    r = None

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60, prefix: str = "rate:"):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix

    def check(self, user_id: str) -> dict:
        now = time.time()
        reset_at = int(now) + self.window_seconds

        if not r:
            logger.warning("Redis is not available, skipping rate limiter")
            return {
                "limit": self.max_requests,
                "remaining": self.max_requests - 1,
                "reset_at": reset_at,
            }

        key = f"{self.prefix}{user_id}"
        window_start = now - self.window_seconds
        member = f"{now}_{uuid.uuid4().hex[:8]}"

        pipeline = r.pipeline()
        pipeline.zremrangebyscore(key, 0, window_start)
        pipeline.zcard(key)
        pipeline.zadd(key, {member: now})
        pipeline.expire(key, self.window_seconds)

        results = pipeline.execute()
        current_count = results[1]
        
        remaining = self.max_requests - (current_count + 1)

        if current_count >= self.max_requests:
            r.zrem(key, member)
            oldest_items = r.zrange(key, 0, 0, withscores=True)
            if oldest_items:
                oldest_score = oldest_items[0][1]
                retry_after = int(oldest_score + self.window_seconds - now) + 1
            else:
                retry_after = self.window_seconds

            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.max_requests} req/min",
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                    "Retry-After": str(retry_after),
                },
            )

        return {
            "limit": self.max_requests,
            "remaining": max(0, remaining),
            "reset_at": reset_at,
        }

# Singleton instances
rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_per_minute, window_seconds=60, prefix="rl:agent:"
)
