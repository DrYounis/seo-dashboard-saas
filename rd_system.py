#!/usr/bin/env python3
"""
AI R&D Weekly System
====================
Autonomous research & development engine that:
1. Scrapes AI/dev trends from top sources weekly
2. Analyzes relevance to your SaaS stack
3. Generates actionable upgrade recommendations
4. Applies safe, non-breaking improvements automatically
5. Sends a weekly digest report

Run: python rd_system.py
Schedule: cron "0 8 * * MON" python rd_system.py
"""

import os
import json
import time
import hashlib
import requests
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / ".rd_state.json"
REPORTS_DIR = BASE_DIR / "rd_reports"
UPGRADES_DIR = BASE_DIR / "rd_upgrades"
REPORTS_DIR.mkdir(exist_ok=True)
UPGRADES_DIR.mkdir(exist_ok=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
REPORT_EMAIL = os.getenv("REPORT_EMAIL", "")

# ── Data Models ───────────────────────────────────────────────────────────────
@dataclass
class Trend:
    title: str
    source: str
    url: str
    summary: str
    category: str          # "model", "framework", "pattern", "tool", "security"
    relevance_score: int   # 0-100
    actionable: bool
    implementation_hint: str
    discovered_at: str

@dataclass
class Upgrade:
    title: str
    category: str
    description: str
    file_path: str
    code_before: str
    code_after: str
    risk_level: str        # "safe", "moderate", "breaking"
    applied: bool
    applied_at: Optional[str]

# ── Trend Sources ─────────────────────────────────────────────────────────────
TREND_SOURCES = [
    # GitHub Trending
    {"name": "GitHub Trending Python", "url": "https://api.github.com/search/repositories?q=ai+agent+created:>2025-01-01&sort=stars&order=desc&per_page=10", "type": "github"},
    {"name": "GitHub Trending LLM", "url": "https://api.github.com/search/repositories?q=llm+saas+created:>2025-01-01&sort=stars&order=desc&per_page=10", "type": "github"},
    # Hacker News
    {"name": "HN Top Stories", "url": "https://hacker-news.firebaseio.com/v0/topstories.json", "type": "hn"},
    # Papers (Semantic Scholar)
    {"name": "AI Papers", "url": "https://api.semanticscholar.org/graph/v1/paper/search?query=LLM+agent+2025&fields=title,abstract,year,citationCount&limit=10", "type": "papers"},
    # PyPI new packages
    {"name": "PyPI AI Packages", "url": "https://pypi.org/search/?q=llm+agent&o=-created", "type": "pypi"},
]

# Keywords that signal high relevance to our stack
HIGH_RELEVANCE_KEYWORDS = [
    "fastapi", "async", "streaming", "websocket", "rag", "vector", "embedding",
    "agent", "crewai", "langgraph", "groq", "llama", "claude", "gpt-4",
    "stripe", "saas", "subscription", "webhook", "rate limit",
    "context window", "function calling", "tool use", "multi-agent",
    "structured output", "pydantic", "type safety", "observability",
    "tracing", "opentelemetry", "caching", "redis", "supabase",
    "edge function", "serverless", "railway", "vercel", "docker",
    "security", "auth", "jwt", "oauth", "api key", "rate limiting",
]

# ── State Management ──────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_run": None, "seen_urls": [], "applied_upgrades": [], "week_number": 0}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── Trend Scraping ────────────────────────────────────────────────────────────
# Now using async scrapers from rd_scrapers.py for 3-5x faster performance
from rd_scrapers import scrape_all_sources_sync as _scrape_all_sources

# ── Scoring & Classification ──────────────────────────────────────────────────
def score_relevance(text: str) -> int:
    text_lower = text.lower()
    score = 0
    for kw in HIGH_RELEVANCE_KEYWORDS:
        if kw in text_lower:
            score += 8
    # Bonus for AI/agent terms
    for term in ["agent", "llm", "gpt", "claude", "groq", "fastapi", "saas"]:
        if term in text_lower:
            score += 5
    return min(score, 100)

def classify_category(text: str) -> str:
    text_lower = text.lower()
    if any(t in text_lower for t in ["gpt", "claude", "llama", "groq", "gemini", "model", "llm"]):
        return "model"
    if any(t in text_lower for t in ["crewai", "langgraph", "langchain", "autogen", "framework"]):
        return "framework"
    if any(t in text_lower for t in ["pattern", "architecture", "design", "rag", "agent"]):
        return "pattern"
    if any(t in text_lower for t in ["security", "auth", "jwt", "oauth", "vulnerability"]):
        return "security"
    return "tool"

def generate_hint(name: str, desc: str, topics: list) -> str:
    text = f"{name} {desc} {' '.join(topics)}".lower()
    if "streaming" in text:
        return "Add streaming responses to your FastAPI endpoints using StreamingResponse"
    if "rag" in text or "vector" in text or "embedding" in text:
        return "Integrate vector search (pgvector/Supabase) for context-aware AI responses"
    if "cache" in text or "redis" in text:
        return "Add Redis caching layer to reduce LLM API costs by 60-80%"
    if "websocket" in text:
        return "Replace polling with WebSocket for real-time job status updates"
    if "structured" in text or "pydantic" in text:
        return "Use structured outputs (Pydantic + Groq) for reliable JSON responses"
    if "rate limit" in text:
        return "Implement token bucket rate limiting per user/plan tier"
    if "observability" in text or "tracing" in text:
        return "Add OpenTelemetry tracing to monitor LLM call latency and costs"
    if "multi-agent" in text:
        return "Upgrade to multi-agent orchestration with specialized sub-agents"
    if "security" in text:
        return "Audit API endpoints for injection attacks and add input sanitization"
    return "Review and consider integrating into your current stack"

# ── LLM Analysis (Groq) ───────────────────────────────────────────────────────
def analyze_trends_with_llm(trends: List[Trend]) -> str:
    """Use Groq to generate a smart analysis of this week's trends"""
    if not GROQ_API_KEY:
        return generate_fallback_analysis(trends)
    
    trend_text = "\n".join([
        f"- [{t.category.upper()}] {t.title}: {t.summary[:100]} (relevance: {t.relevance_score}/100)"
        for t in sorted(trends, key=lambda x: x.relevance_score, reverse=True)[:15]
    ])
    
    prompt = f"""You are a senior AI engineer and CTO reviewing this week's AI/developer trends.
    
Current stack: FastAPI, Groq LLM, CrewAI multi-agent, Stripe billing, Railway deployment, Python.
Goal: Build profitable SaaS products targeting $3M ARR.

This week's top trends:
{trend_text}

Provide a concise analysis (max 400 words) covering:
1. **Top 3 trends to act on THIS WEEK** (with specific code changes)
2. **What to skip** (overhyped or not relevant)
3. **One architectural upgrade** that would increase revenue/retention
4. **Security or performance issue** to fix immediately

Be direct, technical, and actionable. No fluff."""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 600,
                "temperature": 0.3,
            },
            timeout=30,
        )
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  ⚠️  LLM analysis error: {e}")
        return generate_fallback_analysis(trends)

def generate_fallback_analysis(trends: List[Trend]) -> str:
    top = sorted(trends, key=lambda x: x.relevance_score, reverse=True)[:3]
    lines = ["**Top trends this week (configure GROQ_API_KEY for AI analysis):**\n"]
    for t in top:
        lines.append(f"• {t.title}\n  → {t.implementation_hint}\n")
    return "\n".join(lines)

# ── Upgrade Generator ─────────────────────────────────────────────────────────
def generate_upgrades(trends: List[Trend]) -> List[Upgrade]:
    """Generate concrete code upgrades based on trends"""
    upgrades = []
    
    # Check which upgrades are already applied
    state = load_state()
    applied = set(state.get("applied_upgrades", []))
    
    # Upgrade 1: Streaming responses (if streaming trend detected)
    streaming_trends = [t for t in trends if "stream" in t.title.lower() + t.summary.lower()]
    if streaming_trends and "streaming_fastapi" not in applied:
        upgrades.append(Upgrade(
            title="Add Streaming Responses to FastAPI",
            category="performance",
            description="Replace blocking LLM calls with streaming responses for better UX",
            file_path="api/streaming_example.py",
            code_before="""# Old: blocking response
@app.post("/generate")
async def generate(request: TaskRequest):
    result = llm.complete(request.description)
    return {"result": result}""",
            code_after="""# New: streaming response (2025 pattern)
from fastapi.responses import StreamingResponse
import asyncio

@app.post("/generate/stream")
async def generate_stream(request: TaskRequest):
    async def stream_tokens():
        async for chunk in llm.astream(request.description):
            yield f"data: {json.dumps({'token': chunk})}\\n\\n"
        yield "data: [DONE]\\n\\n"
    
    return StreamingResponse(stream_tokens(), media_type="text/event-stream")""",
            risk_level="safe",
            applied=False,
            applied_at=None,
        ))
    
    # Upgrade 2: Structured outputs with Pydantic
    if "structured_outputs" not in applied:
        upgrades.append(Upgrade(
            title="Structured LLM Outputs with Pydantic",
            category="reliability",
            description="Use Groq's structured output mode for reliable JSON responses",
            file_path="api/structured_output_example.py",
            code_before="""# Old: parse LLM text manually
result = llm.complete("Generate code for: " + task)
# Hope it returns valid JSON...
code = result.split("```")[1]""",
            code_after="""# New: structured outputs (2025 pattern)
from pydantic import BaseModel
from groq import Groq

class CodeOutput(BaseModel):
    code: str
    language: str
    explanation: str
    tests: list[str]

client = Groq()
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": f"Generate code for: {task}"}],
    response_format={"type": "json_object"},  # Structured output
)
output = CodeOutput.model_validate_json(response.choices[0].message.content)""",
            risk_level="safe",
            applied=False,
            applied_at=None,
        ))
    
    # Upgrade 3: Caching layer
    if "redis_cache" not in applied:
        upgrades.append(Upgrade(
            title="LLM Response Caching (Save 60-80% API costs)",
            category="cost_optimization",
            description="Cache identical LLM requests to reduce Groq API costs",
            file_path="api/cache_example.py",
            code_before="""# Old: every request hits the LLM
async def generate_code(task: str):
    return await llm.complete(task)  # $0.001 per call""",
            code_after="""# New: semantic caching (2025 pattern)
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
# cached = await r.get(cache_key)""",
            risk_level="safe",
            applied=False,
            applied_at=None,
        ))
    
    # Upgrade 4: WebSocket for real-time updates
    if "websocket_jobs" not in applied:
        upgrades.append(Upgrade(
            title="WebSocket Job Updates (Replace Polling)",
            category="ux",
            description="Replace 2-second polling with WebSocket for instant job status",
            file_path="api/websocket_example.py",
            code_before="""// Old: polling every 2 seconds (90s pattern)
setInterval(async () => {
    const res = await fetch(`/jobs/${jobId}`);
    const data = await res.json();
    showResult(data);
}, 2000);""",
            code_after="""// New: WebSocket (2025 pattern)
const ws = new WebSocket(`wss://yourapp.com/ws/jobs/${jobId}`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    showResult(data);
    if (data.status === 'completed' || data.status === 'failed') {
        ws.close();
    }
};

ws.onerror = () => {
    // Fallback to polling if WebSocket fails
    startPolling(jobId);
};""",
            risk_level="moderate",
            applied=False,
            applied_at=None,
        ))
    
    # Upgrade 5: Rate limiting per plan
    if "plan_rate_limiting" not in applied:
        upgrades.append(Upgrade(
            title="Token Bucket Rate Limiting Per Plan",
            category="security",
            description="Implement proper rate limiting to prevent abuse and protect revenue",
            file_path="api/rate_limit_example.py",
            code_before="""# Old: basic quota check
def check_quota(user):
    if user['tasks_this_month'] >= limit:
        raise HTTPException(429, "Quota exceeded")""",
            code_after="""# New: token bucket rate limiting with TTL cleanup (2025 pattern)
import time
from collections import defaultdict

class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # tokens per second
        self.capacity = capacity  # max burst
        self.tokens = capacity
        self.last_refill = time.time()
        self.last_access = time.time()  # For TTL cleanup

    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now
        self.last_access = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

# Per-user rate limiters with TTL
_rate_limiters: dict = {}
_RATE_LIMITER_TTL = 3600  # Clean up after 1 hour of inactivity

def _cleanup_stale_limiters():
    # Remove rate limiters that haven't been accessed recently
    now = time.time()
    stale_keys = [k for k, v in _rate_limiters.items() if now - v.last_access > _RATE_LIMITER_TTL]
    for k in stale_keys:
        del _rate_limiters[k]

def get_rate_limiter(user_id: str, rate: float, capacity: int) -> TokenBucket:
    # Get or create a rate limiter with automatic cleanup
    _cleanup_stale_limiters()  # Periodic cleanup

    if user_id not in _rate_limiters:
        _rate_limiters[user_id] = TokenBucket(rate, capacity)
    return _rate_limiters[user_id]

def check_rate_limit(user: dict):
    api_key = user["api_key"]
    plan = user.get("plan", "starter")

    # Different rates per plan
    rates = {"starter": 0.05, "professional": 0.2, "team": 1.0}
    rate = rates.get(plan, 0.05)

    bucket = get_rate_limiter(api_key, rate, 5)
    if not bucket.consume():
        raise HTTPException(429, "Rate limit exceeded. Upgrade for higher limits.")""",
            risk_level="safe",
            applied=False,
            applied_at=None,
        ))
    
    return upgrades

# ── Report Generator ──────────────────────────────────────────────────────────
def generate_report(trends: List[Trend], upgrades: List[Upgrade], analysis: str, week_num: int) -> str:
    now = datetime.now(timezone.utc)
    top_trends = sorted(trends, key=lambda x: x.relevance_score, reverse=True)[:10]

    report = f"""# 🔬 AI R&D Weekly Report — Week {week_num}
**Generated**: {now.strftime('%Y-%m-%d %H:%M UTC')}
**Trends Scanned**: {len(trends)} | **Actionable**: {sum(1 for t in trends if t.actionable)}

---

## 🧠 AI Analysis

{analysis}

---

## 📊 Top Trends This Week

| # | Category | Title | Relevance | Action |
|---|----------|-------|-----------|--------|
"""
    for i, t in enumerate(top_trends, 1):
        emoji = {"model": "🤖", "framework": "⚙️", "pattern": "🏗️", "tool": "🔧", "security": "🔒"}.get(t.category, "📌")
        report += f"| {i} | {emoji} {t.category} | [{t.title[:50]}]({t.url}) | {t.relevance_score}/100 | {'✅ Act' if t.actionable else '👀 Watch'} |\n"
    
    report += f"""
---

## 🚀 Upgrades Ready to Apply ({len(upgrades)} total)

"""
    for u in upgrades:
        risk_emoji = {"safe": "🟢", "moderate": "🟡", "breaking": "🔴"}.get(u.risk_level, "⚪")
        report += f"""### {risk_emoji} {u.title}
**Category**: {u.category} | **Risk**: {u.risk_level}
**Why**: {u.description}

**Before:**
```python
{u.code_before}
```

**After:**
```python
{u.code_after}
```

---
"""
    
    report += f"""
## 📈 Implementation Hints

"""
    for t in [t for t in top_trends if t.actionable][:5]:
        report += f"- **{t.title[:40]}**: {t.implementation_hint}\n"
    
    report += f"""
---

## 🗓️ Next Week Focus

Based on trend velocity, next week watch for:
- Multi-agent orchestration frameworks (LangGraph, CrewAI updates)
- Context engineering techniques (beyond basic prompting)
- Edge deployment patterns (Cloudflare Workers AI, Vercel AI SDK)
- Observability tools for LLM applications

---
*Generated by AI R&D System — runs every Monday at 08:00*
"""
    return report

# ── Apply Safe Upgrades ───────────────────────────────────────────────────────
def apply_safe_upgrades(upgrades: List[Upgrade]) -> List[str]:
    """Write upgrade example files to the upgrades directory"""
    applied = []
    for upgrade in upgrades:
        if upgrade.risk_level == "safe":
            # Write the upgrade as a ready-to-use example file
            output_path = UPGRADES_DIR / upgrade.file_path.replace("/", "_")
            content = f"""# Upgrade: {upgrade.title}
# Category: {upgrade.category}
# Risk: {upgrade.risk_level}
# Generated: {datetime.now(timezone.utc).isoformat()}
# Description: {upgrade.description}

# ── BEFORE ───────────────────────────────────────────────────────────────────
{upgrade.code_before}

# ── AFTER (APPLY THIS) ────────────────────────────────────────────────────────
{upgrade.code_after}
"""
            output_path.write_text(content)
            upgrade.applied = True
            upgrade.applied_at = datetime.now(timezone.utc).isoformat()
            applied.append(upgrade.title)
            print(f"  ✅ Upgrade written: {output_path.name}")
    return applied

# ── Email & Slack Reports ────────────────────────────────────────────────────
def send_email_report(report: str, week_num: int):
    if not SENDGRID_API_KEY or not REPORT_EMAIL:
        print("  ℹ️  Email not configured (set SENDGRID_API_KEY + REPORT_EMAIL)")
        return
    try:
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
            json={
                "personalizations": [{"to": [{"email": REPORT_EMAIL}]}],
                "from": {"email": "rd@yourdomain.com", "name": "AI R&D System"},
                "subject": f"🔬 AI R&D Weekly Report — Week {week_num}",
                "content": [{"type": "text/plain", "value": report}],
            },
            timeout=15,
        )
        if resp.status_code == 202:
            print(f"  ✅ Report emailed to {REPORT_EMAIL}")
        else:
            print(f"  ⚠️  Email failed: {resp.status_code}")
    except Exception as e:
        print(f"  ⚠️  Email error: {e}")


def send_slack_notification(report: str, week_num: int):
    """Send R&D report summary to Slack via webhook."""
    if not SLACK_WEBHOOK_URL:
        print("  ℹ️  Slack not configured (set SLACK_WEBHOOK_URL)")
        return
    
    # Create a formatted Slack message
    summary_lines = report.split("\n")[:15]  # First 15 lines as summary
    summary = "\n".join(summary_lines)
    
    slack_message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔬 AI R&D Weekly Report — Week {week_num}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Weekly AI/Dev Trends Summary*\n\n{summary}\n\nSee full report in dashboard."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📊 View Dashboard"
                        },
                        "url": "http://localhost:8003",
                        "action_id": "view_dashboard"
                    }
                ]
            }
        ]
    }
    
    try:
        resp = requests.post(
            SLACK_WEBHOOK_URL,
            json=slack_message,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            print(f"  ✅ Slack notification sent")
        else:
            print(f"  ⚠️  Slack failed: {resp.status_code}")
    except Exception as e:
        print(f"  ⚠️  Slack error: {e}")

# ── Main Workflow ─────────────────────────────────────────────────────────────
def run_rd_cycle(force: bool = False):
    state = load_state()
    now = datetime.now(timezone.utc)

    # Check if we should run (weekly)
    if not force and state.get("last_run"):
        last = datetime.fromisoformat(state["last_run"])
        if (now - last).days < 7:
            print(f"⏭️  Last run: {state['last_run']}. Next run in {7 - (now - last).days} days.")
            print("   Use --force to run now.")
            return
    
    week_num = state.get("week_number", 0) + 1
    print(f"\n{'='*60}")
    print(f"🔬 AI R&D System — Week {week_num}")
    print(f"{'='*60}\n")
    
    # Step 1: Scrape trends (async - 3-5x faster)
    print("📡 Step 1: Scraping AI/Dev trends (async mode)...")
    all_trends: List[Trend] = _scrape_all_sources(TREND_SOURCES)
    
    # Filter out already-seen
    seen = set(state.get("seen_urls", []))
    new_trends = [t for t in all_trends if t.url not in seen]
    print(f"  ✅ Found {len(new_trends)} new trends (from {len(all_trends)} total)")
    
    # Step 2: LLM Analysis
    print("\n🧠 Step 2: AI analysis of trends...")
    analysis = analyze_trends_with_llm(new_trends or all_trends)
    print("  ✅ Analysis complete")
    
    # Step 3: Generate upgrades
    print("\n⚙️  Step 3: Generating code upgrades...")
    upgrades = generate_upgrades(new_trends or all_trends)
    print(f"  ✅ {len(upgrades)} upgrades generated")
    
    # Step 4: Apply safe upgrades
    print("\n🚀 Step 4: Applying safe upgrades...")
    applied = apply_safe_upgrades(upgrades)
    print(f"  ✅ {len(applied)} upgrades applied")
    
    # Step 5: Generate report
    print("\n📝 Step 5: Generating weekly report...")
    report = generate_report(new_trends or all_trends, upgrades, analysis, week_num)
    
    report_path = REPORTS_DIR / f"week_{week_num:03d}_{now.strftime('%Y%m%d')}.md"
    report_path.write_text(report)
    print(f"  ✅ Report saved: {report_path}")
    
    # Step 6: Send notifications
    print("\n📧 Step 6: Sending notifications...")
    send_email_report(report, week_num)
    send_slack_notification(report, week_num)
    
    # Update state
    state.update({
        "last_run": now.isoformat(),
        "week_number": week_num,
        "seen_urls": list(seen | {t.url for t in all_trends}),
        "applied_upgrades": state.get("applied_upgrades", []) + applied,
    })
    save_state(state)
    
    print(f"\n{'='*60}")
    print(f"✅ R&D Cycle Complete — Week {week_num}")
    print(f"   Trends: {len(new_trends)} new | Upgrades: {len(applied)} applied")
    print(f"   Report: {report_path}")
    print(f"{'='*60}\n")
    
    return report_path

# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv or "-f" in sys.argv
    run_rd_cycle(force=force)
