"""
In-Memory Rate Limiter

Giới hạn số request mỗi user trong 1 khoảng thời gian.
Trong production: thay bằng Redis-based rate limiter để scale.

Algorithm: Sliding Window Counter
- Mỗi user có 1 bucket
- Bucket đếm request trong window (60 giây)
- Vượt quá limit → trả về 429 Too Many Requests
"""
import os
import time
import uuid
from fastapi import HTTPException
import logging

try:
    import redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(REDIS_URL, decode_responses=True)
except ImportError:
    r = None

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60, prefix: str = "rate:"):
        """
        Args:
            max_requests: Số request tối đa trong window
            window_seconds: Khoảng thời gian (giây)
            prefix: Tiền tố để lưu dữ liệu trong Redis
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix

    def check(self, user_id: str) -> dict:
        """
        Kiểm tra user có vượt rate limit không bằng Redis Sliding Window.
        Raise 429 nếu vượt quá.
        """
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
        # Loại bỏ các requests cũ
        pipeline.zremrangebyscore(key, 0, window_start)
        # Lấy số lượng requests hiện có trong window
        pipeline.zcard(key)
        # Thêm request hiện tại vào sorted set
        pipeline.zadd(key, {member: now})
        # Đặt TTL cho key bằng window_seconds để tự xoá
        pipeline.expire(key, self.window_seconds)

        results = pipeline.execute()
        current_count = results[1]  # zcard result
        
        remaining = self.max_requests - (current_count + 1)

        if current_count >= self.max_requests:
            # Xoá request vừa thêm vì đã quá giới hạn
            r.zrem(key, member)
            
            oldest_items = r.zrange(key, 0, 0, withscores=True)
            if oldest_items:
                oldest_score = oldest_items[0][1]
                retry_after = int(oldest_score + self.window_seconds - now) + 1
            else:
                retry_after = self.window_seconds

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": self.max_requests,
                    "window_seconds": self.window_seconds,
                    "retry_after_seconds": retry_after,
                },
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

    def get_stats(self, user_id: str) -> dict:
        """Trả về stats của user (không check limit)."""
        if not r:
            return {
                "requests_in_window": 0,
                "limit": self.max_requests,
                "remaining": self.max_requests,
            }

        key = f"{self.prefix}{user_id}"
        now = time.time()
        window_start = now - self.window_seconds

        pipeline = r.pipeline()
        pipeline.zremrangebyscore(key, 0, window_start)
        pipeline.zcard(key)
        results = pipeline.execute()

        active = results[1]
        return {
            "requests_in_window": active,
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - active),
        }


# Singleton instances cho các tiers khác nhau
rate_limiter_user = RateLimiter(max_requests=10, window_seconds=60, prefix="rl:user:")   # User: 10 req/phút
rate_limiter_admin = RateLimiter(max_requests=100, window_seconds=60, prefix="rl:admin:")  # Admin: 100 req/phút
