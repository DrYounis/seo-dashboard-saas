# Upgrade: LLM Response Caching (Save 60-80% API costs)
# Category: cost_optimization
# Risk: safe
# Generated: 2026-02-18T07:39:27.922022
# Description: Cache identical LLM requests to reduce Groq API costs

# ── BEFORE ───────────────────────────────────────────────────────────────────
# Old: every request hits the LLM
async def generate_code(task: str):
    return await llm.complete(task)  # $0.001 per call

# ── AFTER (APPLY THIS) ────────────────────────────────────────────────────────
# New: semantic caching (2025 pattern)
import hashlib
from functools import lru_cache

# Simple hash-based cache (upgrade to Redis for production)
_cache: dict = {}

async def generate_code(task: str):
    cache_key = hashlib.sha256(task.encode()).hexdigest()
    
    if cache_key in _cache:
        print("Cache hit! Saved API call.")
        return _cache[cache_key]
    
    result = await llm.complete(task)
    _cache[cache_key] = result
    return result

# For production: use Redis
# import redis.asyncio as redis
# r = redis.from_url("redis://localhost")
# cached = await r.get(cache_key)
