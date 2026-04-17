"""
Cost Guard — Bảo Vệ Budget LLM

Mục tiêu: Tránh bill bất ngờ từ LLM API.
- Đếm tokens đã dùng mỗi ngày
- Cảnh báo khi gần hết budget
- Block khi vượt budget

Trong production: lưu trong Redis/DB, không phải in-memory.
"""
import os
import time
import logging
from dataclasses import dataclass, field
from fastapi import HTTPException

try:
    import redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(REDIS_URL, decode_responses=True)
except ImportError:
    r = None

logger = logging.getLogger(__name__)


# Giá token (tham khảo, thay đổi theo model)
PRICE_PER_1K_INPUT_TOKENS = 0.00015   # GPT-4o-mini: $0.15/1M input
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006   # GPT-4o-mini: $0.60/1M output


@dataclass
class UsageRecord:
    user_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    request_count: int = 0
    day: str = field(default_factory=lambda: time.strftime("%Y-%m-%d"))

    @property
    def total_cost_usd(self) -> float:
        input_cost = (self.input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS
        output_cost = (self.output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
        return round(input_cost + output_cost, 6)


class CostGuard:
    def __init__(
        self,
        daily_budget_usd: float = 1.0,       # $1/ngày per user
        global_daily_budget_usd: float = 10.0, # $10/ngày tổng cộng
        warn_at_pct: float = 0.8,              # Cảnh báo khi dùng 80%
    ):
        self.daily_budget_usd = daily_budget_usd
        self.global_daily_budget_usd = global_daily_budget_usd
        self.warn_at_pct = warn_at_pct
        self._records: dict[str, UsageRecord] = {}  # Fallback in-memory
        self._global_today = time.strftime("%Y-%m-%d")
        self._global_cost = 0.0

    def _get_redis_key(self, user_id: str, stat_type: str, today: str) -> str:
        return f"cg:{stat_type}:{user_id}:{today}"

    def _get_global_key(self, today: str) -> str:
        return f"cg:global_cost:{today}"

    def _get_record(self, user_id: str) -> UsageRecord:
        today = time.strftime("%Y-%m-%d")
        if not r:
            record = self._records.get(user_id)
            if not record or record.day != today:
                self._records[user_id] = UsageRecord(user_id=user_id, day=today)
            return self._records[user_id]

        pipe = r.pipeline()
        pipe.get(self._get_redis_key(user_id, "input", today))
        pipe.get(self._get_redis_key(user_id, "output", today))
        pipe.get(self._get_redis_key(user_id, "reqs", today))
        res = pipe.execute()

        return UsageRecord(
            user_id=user_id,
            input_tokens=int(res[0] or 0),
            output_tokens=int(res[1] or 0),
            request_count=int(res[2] or 0),
            day=today
        )

    def _get_global_cost(self, today: str) -> float:
        if not r:
            if self._global_today != today:
                self._global_today = today
                self._global_cost = 0.0
            return self._global_cost
        val = r.get(self._get_global_key(today))
        return float(val or 0.0)

    def check_budget(self, user_id: str) -> None:
        """
        Kiểm tra budget trước khi gọi LLM.
        Raise 402 nếu vượt budget.
        """
        today = time.strftime("%Y-%m-%d")
        record = self._get_record(user_id)
        global_cost = self._get_global_cost(today)

        # Global budget check
        if global_cost >= self.global_daily_budget_usd:
            logger.critical(f"GLOBAL BUDGET EXCEEDED: ${global_cost:.4f}")
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable due to budget limits. Try again tomorrow.",
            )

        # Per-user budget check
        if record.total_cost_usd >= self.daily_budget_usd:
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "Daily budget exceeded",
                    "used_usd": record.total_cost_usd,
                    "budget_usd": self.daily_budget_usd,
                    "resets_at": "midnight UTC",
                },
            )

        # Warning khi gần hết budget
        if record.total_cost_usd >= self.daily_budget_usd * self.warn_at_pct:
            logger.warning(
                f"User {user_id} at {record.total_cost_usd/self.daily_budget_usd*100:.0f}% budget"
            )

    def record_usage(
        self, user_id: str, input_tokens: int, output_tokens: int
    ) -> UsageRecord:
        """Ghi nhận usage sau khi gọi LLM xong."""
        today = time.strftime("%Y-%m-%d")
        cost = (input_tokens / 1000 * PRICE_PER_1K_INPUT_TOKENS +
                output_tokens / 1000 * PRICE_PER_1K_OUTPUT_TOKENS)

        if not r:
            record = self._get_record(user_id)
            record.input_tokens += input_tokens
            record.output_tokens += output_tokens
            record.request_count += 1
            if self._global_today != today:
                self._global_today = today
                self._global_cost = 0.0
            self._global_cost += cost
        else:
            pipe = r.pipeline()
            k_in = self._get_redis_key(user_id, "input", today)
            k_out = self._get_redis_key(user_id, "output", today)
            k_reqs = self._get_redis_key(user_id, "reqs", today)
            k_glob = self._get_global_key(today)
            
            pipe.incrby(k_in, input_tokens)
            pipe.incrby(k_out, output_tokens)
            pipe.incr(k_reqs)
            pipe.incrbyfloat(k_glob, cost)
            
            # Thời gian lưu trữ Redis keys (32 days ~ 1 month context)
            ttl = 32 * 24 * 3600
            pipe.expire(k_in, ttl)
            pipe.expire(k_out, ttl)
            pipe.expire(k_reqs, ttl)
            pipe.expire(k_glob, ttl)
            
            pipe.execute()

        record = self._get_record(user_id)
        logger.info(
            f"Usage: user={user_id} req={record.request_count} "
            f"cost=${record.total_cost_usd:.4f}/{self.daily_budget_usd}"
        )
        return record

    def get_usage(self, user_id: str) -> dict:
        record = self._get_record(user_id)
        return {
            "user_id": user_id,
            "date": record.day,
            "requests": record.request_count,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "cost_usd": record.total_cost_usd,
            "budget_usd": self.daily_budget_usd,
            "budget_remaining_usd": max(0, self.daily_budget_usd - record.total_cost_usd),
            "budget_used_pct": round(record.total_cost_usd / self.daily_budget_usd * 100, 1),
        }


# Singleton
cost_guard = CostGuard(daily_budget_usd=1.0, global_daily_budget_usd=10.0)
