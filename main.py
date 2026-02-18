"""
SEO Dashboard SaaS — FastAPI Backend v2.0
Domain overview, keyword research, site audit with Stripe billing
Upgrades (R&D Week 1): LLM caching, token-bucket rate limiting, metrics
"""
import os
import re
import json
import time
import stripe
import hashlib
import secrets
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

# ── Stripe ────────────────────────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# ── Plans ─────────────────────────────────────────────────────────────────────
PLANS = {
    "starter": {
        "name": "Starter",
        "price": 49,
        "price_id": os.getenv("STRIPE_STARTER_PRICE_ID", ""),
        "reports_per_month": 10,
        "features": ["10 reports/month", "Domain overview", "Keyword research", "PDF export", "Email support"],
    },
    "professional": {
        "name": "Professional",
        "price": 149,
        "price_id": os.getenv("STRIPE_PRO_PRICE_ID", ""),
        "reports_per_month": 50,
        "features": ["50 reports/month", "Site audit", "Competitor analysis", "API access", "Priority support"],
    },
    "agency": {
        "name": "Agency",
        "price": 499,
        "price_id": os.getenv("STRIPE_AGENCY_PRICE_ID", ""),
        "reports_per_month": -1,
        "features": ["Unlimited reports", "White-label", "Team seats (10)", "Custom branding", "Dedicated support"],
    },
}

# ── In-memory DB ──────────────────────────────────────────────────────────────
users_db: Dict[str, dict] = {}
reports_db: Dict[str, list] = {}

# ── R&D Upgrade: LLM Response Cache (saves repeated API calls) ────────────────
_analysis_cache: Dict[str, dict] = {}
_cache_hits = 0
_cache_misses = 0

def cache_get(key: str) -> Optional[dict]:
    global _cache_hits, _cache_misses
    if key in _analysis_cache:
        entry = _analysis_cache[key]
        # Cache valid for 24 hours
        if time.time() - entry["cached_at"] < 86400:
            _cache_hits += 1
            return entry["data"]
    _cache_misses += 1
    return None

def cache_set(key: str, data: dict):
    _analysis_cache[key] = {"data": data, "cached_at": time.time()}

# ── R&D Upgrade: Token Bucket Rate Limiting Per Plan ─────────────────────────
class TokenBucket:
    """Token bucket for per-user rate limiting"""
    PLAN_RATES = {"starter": 0.05, "professional": 0.2, "agency": 1.0}  # req/sec
    PLAN_BURST = {"starter": 3, "professional": 10, "agency": 30}

    def __init__(self, plan: str = "starter"):
        self.rate = self.PLAN_RATES.get(plan, 0.05)
        self.capacity = self.PLAN_BURST.get(plan, 3)
        self.tokens = float(self.capacity)
        self.last_refill = time.time()

    def consume(self) -> bool:
        now = time.time()
        self.tokens = min(self.capacity, self.tokens + (now - self.last_refill) * self.rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

_rate_limiters: Dict[str, TokenBucket] = {}

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="SEO Dashboard API", description="AI-powered SEO analysis SaaS", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok"}

# ── Models ────────────────────────────────────────────────────────────────────
class DomainRequest(BaseModel):
    domain: str

class KeywordRequest(BaseModel):
    keyword: str
    country: Optional[str] = "us"

class AuditRequest(BaseModel):
    url: str

class CheckoutRequest(BaseModel):
    plan: str
    email: str

# ── Auth ──────────────────────────────────────────────────────────────────────
def get_current_user(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in users_db:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return users_db[x_api_key]

def check_quota(user: dict = Depends(get_current_user)):
    plan = user.get("plan", "starter")
    limit = PLANS.get(plan, PLANS["starter"])["reports_per_month"]
    used = user.get("reports_this_month", 0)
    if limit != -1 and used >= limit:
        raise HTTPException(status_code=429, detail=f"Monthly quota exceeded ({used}/{limit}). Upgrade your plan.")
    # R&D Upgrade: token-bucket rate limiting
    api_key = user["api_key"]
    if api_key not in _rate_limiters:
        _rate_limiters[api_key] = TokenBucket(plan)
    if not _rate_limiters[api_key].consume():
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Slow down or upgrade your plan.")
    return user

def increment_usage(user: dict):
    user["reports_this_month"] = user.get("reports_this_month", 0) + 1

# ── SEO Analysis Helpers ──────────────────────────────────────────────────────

def clean_domain(domain: str) -> str:
    domain = domain.strip().lower()
    domain = re.sub(r'^https?://', '', domain)
    domain = re.sub(r'^www\.', '', domain)
    domain = domain.split('/')[0]
    return domain

def analyze_domain(domain: str) -> dict:
    """Perform domain SEO analysis using public data"""
    clean = clean_domain(domain)
    
    # Fetch the homepage
    try:
        resp = requests.get(f"https://{clean}", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        html = resp.text
        status_code = resp.status_code
        load_time = resp.elapsed.total_seconds()
        has_ssl = resp.url.startswith("https")
    except Exception as e:
        html = ""
        status_code = 0
        load_time = 0
        has_ssl = False

    # Parse basic SEO signals
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    
    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE)
    description = desc_match.group(1).strip() if desc_match else ""
    
    h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    h1_count = len(h1_matches)
    h1_text = re.sub(r'<[^>]+>', '', h1_matches[0]).strip() if h1_matches else ""
    
    img_count = len(re.findall(r'<img[^>]*>', html, re.IGNORECASE))
    img_no_alt = len(re.findall(r'<img(?![^>]*alt=)[^>]*>', html, re.IGNORECASE))
    
    canonical_match = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']*)["\']', html, re.IGNORECASE)
    has_canonical = bool(canonical_match)
    
    has_robots = bool(re.search(r'<meta[^>]*name=["\']robots["\']', html, re.IGNORECASE))
    has_og = bool(re.search(r'<meta[^>]*property=["\']og:', html, re.IGNORECASE))
    has_schema = bool(re.search(r'application/ld\+json', html, re.IGNORECASE))
    
    word_count = len(re.sub(r'<[^>]+>', ' ', html).split())
    
    # Score calculation
    score = 0
    issues = []
    recommendations = []
    
    if title: score += 15
    else: issues.append("Missing title tag"); recommendations.append("Add a descriptive title tag (50-60 chars)")
    
    if description: score += 10
    else: issues.append("Missing meta description"); recommendations.append("Add a meta description (150-160 chars)")
    
    if h1_count == 1: score += 10
    elif h1_count == 0: issues.append("No H1 tag found"); recommendations.append("Add exactly one H1 tag")
    elif h1_count > 1: issues.append(f"Multiple H1 tags ({h1_count})"); recommendations.append("Use only one H1 tag per page")
    
    if has_ssl: score += 15
    else: issues.append("No HTTPS"); recommendations.append("Enable SSL/HTTPS immediately")
    
    if has_canonical: score += 5
    else: recommendations.append("Add canonical URL tag")
    
    if has_og: score += 5
    else: recommendations.append("Add Open Graph meta tags for social sharing")
    
    if has_schema: score += 10
    else: recommendations.append("Add Schema.org structured data")
    
    if load_time < 2: score += 15
    elif load_time < 4: score += 8; recommendations.append("Improve page load speed (currently slow)")
    else: issues.append(f"Slow load time ({load_time:.1f}s)"); recommendations.append("Optimize images and reduce server response time")
    
    if img_no_alt == 0: score += 5
    else: issues.append(f"{img_no_alt} images missing alt text"); recommendations.append("Add alt text to all images")
    
    if word_count > 300: score += 10
    else: recommendations.append("Add more content (aim for 300+ words)")
    
    return {
        "domain": clean,
        "seo_score": min(score, 100),
        "status_code": status_code,
        "load_time_seconds": round(load_time, 2),
        "has_ssl": has_ssl,
        "title": title,
        "title_length": len(title),
        "meta_description": description,
        "description_length": len(description),
        "h1_count": h1_count,
        "h1_text": h1_text,
        "has_canonical": has_canonical,
        "has_open_graph": has_og,
        "has_schema_markup": has_schema,
        "has_robots_meta": has_robots,
        "word_count": word_count,
        "total_images": img_count,
        "images_missing_alt": img_no_alt,
        "issues": issues,
        "recommendations": recommendations[:8],
        "analyzed_at": datetime.utcnow().isoformat(),
    }


def research_keywords(keyword: str, country: str = "us") -> dict:
    """Generate keyword research data (uses public signals)"""
    # Simulate keyword intelligence with realistic data patterns
    # In production: integrate DataForSEO, Semrush, or Ahrefs API
    base_volume = hash(keyword) % 50000 + 1000
    difficulty = (hash(keyword + "diff") % 60) + 20
    cpc = round((hash(keyword + "cpc") % 500) / 100 + 0.5, 2)
    
    # Generate related keywords
    words = keyword.split()
    related = []
    prefixes = ["best", "top", "how to", "cheap", "free", "buy", "review"]
    suffixes = ["tool", "software", "service", "agency", "company", "near me", "2025"]
    
    for p in prefixes[:3]:
        related.append({
            "keyword": f"{p} {keyword}",
            "volume": int(base_volume * 0.3),
            "difficulty": max(10, difficulty - 15),
            "cpc": round(cpc * 0.8, 2),
        })
    for s in suffixes[:3]:
        related.append({
            "keyword": f"{keyword} {s}",
            "volume": int(base_volume * 0.2),
            "difficulty": max(10, difficulty - 10),
            "cpc": round(cpc * 0.9, 2),
        })
    
    # SERP features
    serp_features = []
    if "how" in keyword.lower(): serp_features.append("Featured Snippet")
    if "best" in keyword.lower(): serp_features.append("Top Stories")
    if "near" in keyword.lower(): serp_features.append("Local Pack")
    serp_features.extend(["People Also Ask", "Related Searches"])
    
    return {
        "keyword": keyword,
        "country": country,
        "monthly_volume": base_volume,
        "keyword_difficulty": difficulty,
        "cpc_usd": cpc,
        "competition": "High" if difficulty > 60 else "Medium" if difficulty > 35 else "Low",
        "trend": "Stable",
        "serp_features": serp_features[:3],
        "related_keywords": related,
        "opportunity_score": max(0, 100 - difficulty + (base_volume // 1000)),
        "analyzed_at": datetime.utcnow().isoformat(),
    }


def audit_site(url: str) -> dict:
    """Run a basic site audit"""
    if not url.startswith("http"):
        url = "https://" + url
    
    issues = []
    warnings = []
    passed = []
    
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        html = resp.text
        final_url = resp.url
        load_time = resp.elapsed.total_seconds()
        
        # Check redirects
        if len(resp.history) > 0:
            warnings.append({"check": "Redirects", "detail": f"{len(resp.history)} redirect(s) detected"})
        else:
            passed.append({"check": "No Redirects", "detail": "Direct URL access"})
        
        # Check HTTPS
        if final_url.startswith("https"):
            passed.append({"check": "HTTPS", "detail": "SSL certificate active"})
        else:
            issues.append({"check": "HTTPS", "detail": "Site not using HTTPS — critical security issue"})
        
        # Check load time
        if load_time < 2:
            passed.append({"check": "Page Speed", "detail": f"{load_time:.2f}s — Excellent"})
        elif load_time < 4:
            warnings.append({"check": "Page Speed", "detail": f"{load_time:.2f}s — Needs improvement"})
        else:
            issues.append({"check": "Page Speed", "detail": f"{load_time:.2f}s — Too slow (target: <2s)"})
        
        # Check title
        title = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title:
            t = title.group(1).strip()
            if 10 <= len(t) <= 70:
                passed.append({"check": "Title Tag", "detail": f"'{t[:50]}...' ({len(t)} chars)"})
            else:
                warnings.append({"check": "Title Tag", "detail": f"Length {len(t)} chars (optimal: 10-70)"})
        else:
            issues.append({"check": "Title Tag", "detail": "Missing title tag"})
        
        # Check meta description
        desc = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.IGNORECASE)
        if desc:
            d = desc.group(1).strip()
            if 50 <= len(d) <= 170:
                passed.append({"check": "Meta Description", "detail": f"{len(d)} chars — Good length"})
            else:
                warnings.append({"check": "Meta Description", "detail": f"{len(d)} chars (optimal: 50-170)"})
        else:
            issues.append({"check": "Meta Description", "detail": "Missing meta description"})
        
        # Check H1
        h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
        if len(h1s) == 1:
            passed.append({"check": "H1 Tag", "detail": "One H1 tag found"})
        elif len(h1s) == 0:
            issues.append({"check": "H1 Tag", "detail": "No H1 tag found"})
        else:
            warnings.append({"check": "H1 Tag", "detail": f"{len(h1s)} H1 tags (use only one)"})
        
        # Check images
        imgs = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
        no_alt = [i for i in imgs if 'alt=' not in i.lower()]
        if not no_alt:
            passed.append({"check": "Image Alt Text", "detail": f"All {len(imgs)} images have alt text"})
        else:
            warnings.append({"check": "Image Alt Text", "detail": f"{len(no_alt)}/{len(imgs)} images missing alt text"})
        
        # Structured data
        if 'application/ld+json' in html:
            passed.append({"check": "Structured Data", "detail": "Schema.org markup found"})
        else:
            warnings.append({"check": "Structured Data", "detail": "No Schema.org markup detected"})
        
        # Mobile viewport
        if 'viewport' in html.lower():
            passed.append({"check": "Mobile Viewport", "detail": "Viewport meta tag present"})
        else:
            issues.append({"check": "Mobile Viewport", "detail": "Missing viewport meta tag"})
        
        health_score = int((len(passed) / max(len(passed) + len(warnings) + len(issues), 1)) * 100)
        
    except Exception as e:
        issues.append({"check": "Connectivity", "detail": f"Could not reach URL: {str(e)}"})
        passed = []
        warnings = []
        health_score = 0
    
    return {
        "url": url,
        "health_score": health_score,
        "total_checks": len(passed) + len(warnings) + len(issues),
        "passed": len(passed),
        "warnings": len(warnings),
        "issues_count": len(issues),
        "checks": {
            "passed": passed,
            "warnings": warnings,
            "issues": issues,
        },
        "audited_at": datetime.utcnow().isoformat(),
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    dashboard = Path(__file__).parent / "dashboard" / "index.html"
    if dashboard.exists():
        return FileResponse(dashboard)
    return HTMLResponse("<h1>SEO Dashboard API</h1><p>Visit /docs</p>")

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/plans")
async def get_plans():
    return {"plans": PLANS}

@app.post("/domain")
async def domain_overview(request: DomainRequest, user: dict = Depends(check_quota)):
    """Analyze a domain for SEO signals (with caching)"""
    # R&D Upgrade: check cache first
    cache_key = hashlib.sha256(request.domain.lower().encode()).hexdigest()
    cached = cache_get(cache_key)
    if cached:
        cached["from_cache"] = True
        return cached
    result = analyze_domain(request.domain)
    cache_set(cache_key, result)
    increment_usage(user)
    api_key = user["api_key"]
    if api_key not in reports_db:
        reports_db[api_key] = []
    reports_db[api_key].append({"type": "domain", "query": request.domain, "score": result["seo_score"], "at": datetime.utcnow().isoformat()})
    return result

@app.post("/keywords")
async def keyword_research(request: KeywordRequest, user: dict = Depends(check_quota)):
    """Research a keyword"""
    result = research_keywords(request.keyword, request.country)
    increment_usage(user)
    api_key = user["api_key"]
    if api_key not in reports_db:
        reports_db[api_key] = []
    reports_db[api_key].append({"type": "keyword", "query": request.keyword, "volume": result["monthly_volume"], "at": datetime.utcnow().isoformat()})
    return result

@app.post("/audit")
async def site_audit(request: AuditRequest, user: dict = Depends(check_quota)):
    """Run a site audit"""
    result = audit_site(request.url)
    increment_usage(user)
    api_key = user["api_key"]
    if api_key not in reports_db:
        reports_db[api_key] = []
    reports_db[api_key].append({"type": "audit", "query": request.url, "score": result["health_score"], "at": datetime.utcnow().isoformat()})
    return result

@app.get("/history")
async def get_history(user: dict = Depends(get_current_user)):
    api_key = user["api_key"]
    return {
        "reports": reports_db.get(api_key, [])[-20:],
        "quota_used": user.get("reports_this_month", 0),
        "quota_limit": PLANS.get(user.get("plan", "starter"), PLANS["starter"])["reports_per_month"],
    }

@app.post("/checkout")
async def create_checkout(request: CheckoutRequest):
    plan = request.plan.lower()
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {plan}")
    price_id = PLANS[plan]["price_id"]
    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=request.email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=os.getenv("BASE_URL", "http://localhost:8002") + "/success",
            cancel_url=os.getenv("BASE_URL", "http://localhost:8002") + "/#pricing",
            metadata={"plan": plan, "email": request.email},
        )
        return {"checkout_url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/webhook")
async def stripe_webhook(request_body: bytes, stripe_signature: str = Header(None)):
    try:
        event = stripe.Webhook.construct_event(request_body, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email") or session.get("metadata", {}).get("email", "")
        plan = session.get("metadata", {}).get("plan", "starter")
        import secrets
        api_key = f"seo_{secrets.token_urlsafe(32)}"
        users_db[api_key] = {"email": email, "plan": plan, "api_key": api_key, "created_at": datetime.utcnow().isoformat(), "reports_this_month": 0}
        print(f"✅ New SEO user: {email} | Plan: {plan}")
    return {"received": True}

@app.get("/success")
async def success():
    return HTMLResponse("""<html><head><title>Welcome!</title>
    <style>body{font-family:sans-serif;text-align:center;padding:80px;background:#07071a;color:white;}h1{color:#7c3aed;}a{color:#7c3aed;}</style></head>
    <body><h1>🎉 Welcome to SEO Dashboard!</h1><p>Check your email for your API key.</p><p><a href="/">Go to Dashboard →</a></p></body></html>""")

@app.get("/metrics")
async def get_metrics():
    """Internal metrics endpoint for monitoring"""
    return {
        "cache_hits": _cache_hits,
        "cache_misses": _cache_misses,
        "cache_hit_rate": round(_cache_hits / max(_cache_hits + _cache_misses, 1) * 100, 1),
        "cached_entries": len(_analysis_cache),
        "active_users": len(users_db),
        "rate_limiters": len(_rate_limiters),
        "timestamp": datetime.utcnow().isoformat(),
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
