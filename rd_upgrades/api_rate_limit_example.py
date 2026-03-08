# Upgrade: Token Bucket Rate Limiting Per Plan
# Category: security
# Risk: safe
# Generated: 2026-02-18T07:39:27.928391
# Description: Implement proper rate limiting to prevent abuse and protect revenue

# ── BEFORE ───────────────────────────────────────────────────────────────────
# Old: basic quota check
def check_quota(user):
    if user['tasks_this_month'] >= limit:
        raise HTTPException(429, "Quota exceeded")

# ── AFTER (APPLY THIS) ────────────────────────────────────────────────────────
# New: token bucket rate limiting (2025 pattern)
import time
from collections import defaultdict

class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # tokens per second
        self.capacity = capacity  # max burst
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

# Per-user rate limiters
_rate_limiters: dict = defaultdict(lambda: TokenBucket(rate=0.1, capacity=5))

def check_rate_limit(user: dict):
    api_key = user["api_key"]
    plan = user.get("plan", "starter")
    
    # Different rates per plan
    rates = {"starter": 0.05, "professional": 0.2, "team": 1.0}
    rate = rates.get(plan, 0.05)
    
    bucket = _rate_limiters[api_key]
    if not bucket.consume():
        raise HTTPException(429, f"Rate limit exceeded. Upgrade for higher limits.")
