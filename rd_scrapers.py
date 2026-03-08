#!/usr/bin/env python3
"""
Async Trend Scrapers — Fast parallel scraping with aiohttp
"""
import asyncio
import aiohttp
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Trend:
    """Trend data model - duplicate import to avoid circular dependency."""
    title: str
    source: str
    url: str
    summary: str
    category: str
    relevance_score: int
    actionable: bool
    implementation_hint: str
    discovered_at: str


def score_relevance(text: str) -> int:
    """Score text relevance to our stack."""
    HIGH_RELEVANCE_KEYWORDS = [
        "fastapi", "async", "streaming", "websocket", "rag", "vector", "embedding",
        "agent", "crewai", "langgraph", "groq", "llama", "claude", "gpt-4",
        "stripe", "saas", "subscription", "webhook", "rate limit",
    ]
    text_lower = text.lower()
    score = 0
    for kw in HIGH_RELEVANCE_KEYWORDS:
        if kw in text_lower:
            score += 8
    for term in ["agent", "llm", "gpt", "claude", "groq", "fastapi", "saas"]:
        if term in text_lower:
            score += 5
    return min(score, 100)


def classify_category(text: str) -> str:
    """Classify trend into category."""
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
    """Generate implementation hint based on trend content."""
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


@dataclass
class ScrapingResult:
    source: str
    trends: List[Trend]
    error: Optional[str] = None


async def scrape_github_trending(
    session: aiohttp.ClientSession, 
    url: str, 
    source_name: str
) -> ScrapingResult:
    """Scrape GitHub trending repos asynchronously."""
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if os.getenv("GITHUB_TOKEN"):
            headers["Authorization"] = f"token {os.getenv('GITHUB_TOKEN')}"
        
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
            items = data.get("items", [])
            
            trends = []
            for item in items[:5]:
                name = item.get("full_name", "")
                desc = item.get("description", "") or ""
                stars = item.get("stargazers_count", 0)
                lang = item.get("language", "")
                topics = item.get("topics", [])
                
                relevance = score_relevance(f"{name} {desc} {' '.join(topics)}")
                
                trends.append(Trend(
                    title=f"🌟 {name} ({stars:,} stars)",
                    source=source_name,
                    url=item.get("html_url", ""),
                    summary=f"{desc} | Language: {lang} | Stars: {stars:,}",
                    category=classify_category(f"{name} {desc}"),
                    relevance_score=relevance,
                    actionable=relevance > 50,
                    implementation_hint=generate_hint(name, desc, topics),
                    discovered_at=datetime.now(timezone.utc).isoformat(),
                ))
            
            return ScrapingResult(source=source_name, trends=trends)
            
    except Exception as e:
        return ScrapingResult(source=source_name, trends=[], error=str(e))


async def scrape_hn(
    session: aiohttp.ClientSession, 
    url: str, 
    source_name: str
) -> ScrapingResult:
    """Scrape Hacker News top stories asynchronously."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            story_ids = await resp.json()
            
            # Fetch top 30 stories in parallel
            story_tasks = []
            for sid in story_ids[:30]:
                story_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                story_tasks.append(session.get(story_url, timeout=aiohttp.ClientTimeout(total=5)))
            
            story_responses = await asyncio.gather(*story_tasks, return_exceptions=True)
            
            trends = []
            for story_resp in story_responses:
                if isinstance(story_resp, Exception):
                    continue
                    
                async with story_resp as story_resp:
                    story = await story_resp.json()
                    if not story or story.get("type") != "story":
                        continue
                    
                    title = story.get("title", "")
                    text = story.get("text", "") or ""
                    url_s = story.get("url", "")
                    
                    relevance = score_relevance(f"{title} {text}")
                    if relevance > 30:
                        trends.append(Trend(
                            title=f"📰 {title}",
                            source="Hacker News",
                            url=url_s or f"https://news.ycombinator.com/item?id={story.get('id')}",
                            summary=f"HN Score: {story.get('score', 0)} | Comments: {story.get('descendants', 0)}",
                            category=classify_category(title),
                            relevance_score=relevance,
                            actionable=relevance > 60,
                            implementation_hint=generate_hint(title, "", []),
                            discovered_at=datetime.now(timezone.utc).isoformat(),
                        ))
            
            # Sort by relevance and take top 5
            trends.sort(key=lambda t: t.relevance_score, reverse=True)
            return ScrapingResult(source=source_name, trends=trends[:5])
            
    except Exception as e:
        return ScrapingResult(source=source_name, trends=[], error=str(e))


async def scrape_papers(
    session: aiohttp.ClientSession, 
    url: str, 
    source_name: str
) -> ScrapingResult:
    """Scrape AI papers from Semantic Scholar asynchronously."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.json()
            papers = data.get("data", [])
            
            trends = []
            for paper in papers[:5]:
                title = paper.get("title", "")
                abstract = paper.get("abstract", "") or ""
                citations = paper.get("citationCount", 0)
                
                relevance = score_relevance(f"{title} {abstract}")
                if relevance > 20:
                    trends.append(Trend(
                        title=f"📄 {title}",
                        source="Semantic Scholar",
                        url=f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                        summary=abstract[:200] + "..." if len(abstract) > 200 else abstract,
                        category=classify_category(f"{title} {abstract}"),
                        relevance_score=relevance,
                        actionable=relevance > 50,
                        implementation_hint=generate_hint(title, abstract, []),
                        discovered_at=datetime.now(timezone.utc).isoformat(),
                    ))
            
            return ScrapingResult(source=source_name, trends=trends)
            
    except Exception as e:
        return ScrapingResult(source=source_name, trends=[], error=str(e))


async def scrape_all_sources(sources: List[Dict]) -> List[Trend]:
    """
    Scrape all sources in parallel using async I/O.
    Returns combined list of all trends.
    """
    async with aiohttp.ClientSession() as session:
        # Create tasks for all sources
        tasks = []
        for source in sources:
            if source["type"] == "github":
                tasks.append(scrape_github_trending(session, source["url"], source["name"]))
            elif source["type"] == "hn":
                tasks.append(scrape_hn(session, source["url"], source["name"]))
            elif source["type"] == "papers":
                tasks.append(scrape_papers(session, source["url"], source["name"]))
        
        # Run all scrapers in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all trends
        all_trends = []
        for result in results:
            if isinstance(result, Exception):
                print(f"  ⚠️  Scraper error: {result}")
            elif isinstance(result, ScrapingResult):
                if result.error:
                    print(f"  ⚠️  {result.source}: {result.error}")
                all_trends.extend(result.trends)
                print(f"  ✅ {result.source}: {len(result.trends)} trends")
        
        return all_trends


# Sync wrapper for backward compatibility
def scrape_all_sources_sync(sources: List[Dict]) -> List[Trend]:
    """Synchronous wrapper for scrape_all_sources."""
    return asyncio.run(scrape_all_sources(sources))
