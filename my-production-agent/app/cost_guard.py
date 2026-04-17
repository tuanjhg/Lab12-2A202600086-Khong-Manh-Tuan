import time
import logging
from dataclasses import dataclass, field
from fastapi import HTTPException
from app.config import settings

try:
    import redis
    r = redis.from_url(settings.redis_url, decode_responses=True)
except ImportError:
    r = None

logger = logging.getLogger(__name__)

PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006

class CostGuard:
    def __init__(self, daily_budget_usd: float = 10.0, warn_at_pct: float = 0.8):
        self.daily_budget_usd = daily_budget_usd
        self.warn_at_pct = warn_at_pct

    def _get_redis_key(self, user_id: str, today: str) -> str:
        return f"cg:cost:{user_id}:{today}"

    def check_and_record_cost(self, user_id: str, input_tokens: int, output_tokens: int):
        today = time.strftime("%Y-%m-%d")
        cost = (input_tokens / 1000 * PRICE_PER_1K_INPUT_TOKENS +
                output_tokens / 1000 * PRICE_PER_1K_OUTPUT_TOKENS)

        if not r:
            logger.warning("Redis is not available, skipping Cost Guard tracking")
            return
            
        key = self._get_redis_key(user_id, today)
        current_cost = float(r.get(key) or 0.0)
        
        # Check limit
        if current_cost >= self.daily_budget_usd:
            logger.critical(f"BUDGET EXCEEDED: ${current_cost:.4f}")
            raise HTTPException(
                status_code=402,
                detail=f"Daily budget of ${self.daily_budget_usd} exceeded.",
            )

        # Warning
        if current_cost >= self.daily_budget_usd * self.warn_at_pct:
            logger.warning(f"User {user_id} at {current_cost/self.daily_budget_usd*100:.0f}% budget")
            
        # Record usage
        if cost > 0:
            pipeline = r.pipeline()
            pipeline.incrbyfloat(key, cost)
            pipeline.expire(key, 32 * 24 * 3600)  # ~1 month retetion
            pipeline.execute()

cost_guard = CostGuard(daily_budget_usd=settings.daily_budget_usd)
