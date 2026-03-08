#!/usr/bin/env python3
"""
R&D Dashboard API — FastAPI server for the R&D web UI
Serves the dashboard and exposes R&D data via REST
"""
import json
import time
import sys
import subprocess
import re
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import uvicorn
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "rd_reports"
UPGRADES_DIR = BASE_DIR / "rd_upgrades"
STATE_FILE = BASE_DIR / ".rd_state.json"

# Track service start time for health endpoint
_service_start_time: float = time.time()

# Rate limiting: track last run time
_last_run_time: float = 0
_RATE_LIMIT_COOLDOWN = 300  # 5 minutes between runs

# API Key for authentication (set via environment variable)
DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "")

app = FastAPI(title="AI R&D Dashboard")
# Restrict CORS to localhost in production
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8003", "http://127.0.0.1:8003"], allow_methods=["*"], allow_headers=["*"])


def _validate_filename(name: str) -> bool:
    """Validate filename to prevent path traversal attacks."""
    if ".." in name or "/" in name or "\\" in name:
        return False
    # Only allow alphanumeric, dash, underscore, dot
    return bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', name))


def _load_state_safe() -> Dict[str, Any]:
    """Safely load state file with error handling for corrupted JSON."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load state file: {e}")
    return {"last_run": None, "week_number": 0, "applied_upgrades": [], "last_error": None}


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint — required by watchdog on port 8003."""
    elapsed = time.time() - _service_start_time
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": f"{elapsed:.1f}s",
        "service": "rd-dashboard-api",
    }


@app.get("/", response_class=HTMLResponse)
async def root() -> FileResponse:
    return FileResponse(BASE_DIR / "rd_dashboard.html")


@app.get("/api/state")
async def get_state() -> Dict[str, Any]:
    state = _load_state_safe()
    return state


@app.get("/api/reports")
async def list_reports() -> Dict[str, List[Dict[str, Any]]]:
    if not REPORTS_DIR.exists():
        return {"reports": []}
    reports = sorted(REPORTS_DIR.glob("*.md"), reverse=True)
    return {"reports": [{"name": r.name, "size": r.stat().st_size, "modified": r.stat().st_mtime} for r in reports[:10]]}


@app.get("/api/reports/{name}")
async def get_report(name: str) -> Dict[str, str]:
    if not _validate_filename(name):
        raise HTTPException(status_code=400, detail="Invalid report name")
    path = REPORTS_DIR / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    return {"content": path.read_text()}


@app.get("/api/upgrades")
async def list_upgrades() -> Dict[str, List[Dict[str, Any]]]:
    if not UPGRADES_DIR.exists():
        return {"upgrades": []}
    upgrades = sorted(UPGRADES_DIR.glob("*.py"), reverse=True)
    return {"upgrades": [{"name": u.name, "size": u.stat().st_size} for u in upgrades]}


@app.get("/api/upgrades/{name}")
async def get_upgrade(name: str) -> Dict[str, str]:
    if not _validate_filename(name):
        raise HTTPException(status_code=400, detail="Invalid upgrade name")
    path = UPGRADES_DIR / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Upgrade not found")
    return {"content": path.read_text()}


@app.get("/api/config")
async def get_config() -> Dict[str, str]:
    """Return dynamic configuration for the dashboard."""
    return {"script_dir": str(BASE_DIR)}


@app.get("/api/trends")
async def list_trends(
    category: str = None,
    min_relevance: int = 0,
    search: str = None,
    limit: int = 50
) -> Dict[str, List[Dict[str, Any]]]:
    """
    List trends with optional filtering.
    
    Query params:
    - category: Filter by category (model, framework, pattern, tool, security)
    - min_relevance: Minimum relevance score (0-100)
    - search: Search in title and summary
    - limit: Maximum number of trends to return (default 50)
    """
    from rd_system import Trend
    
    # Load latest report to get trends
    if not REPORTS_DIR.exists():
        return {"trends": []}
    
    reports = sorted(REPORTS_DIR.glob("*.md"), reverse=True)
    if not reports:
        return {"trends": []}
    
    # Parse trends from latest report (or use state file)
    # For now, return empty - trends are in reports
    return {"trends": []}


@app.get("/api/trends/live")
async def get_live_trends(
    category: str = None,
    min_relevance: int = 0,
    search: str = None
) -> Dict[str, Any]:
    """
    Fetch live trends from sources with filtering.
    Uses async scraping for fast results.
    """
    import time
    from rd_scrapers import scrape_all_sources
    from rd_system import TREND_SOURCES
    
    start = time.time()
    
    # Scrape live trends
    all_trends = await scrape_all_sources(TREND_SOURCES)
    
    # Apply filters
    filtered = all_trends
    
    if category:
        filtered = [t for t in filtered if t.category == category.lower()]
    
    if min_relevance > 0:
        filtered = [t for t in filtered if t.relevance_score >= min_relevance]
    
    if search:
        search_lower = search.lower()
        filtered = [
            t for t in filtered 
            if search_lower in t.title.lower() or search_lower in t.summary.lower()
        ]
    
    # Sort by relevance
    filtered.sort(key=lambda t: t.relevance_score, reverse=True)
    
    return {
        "trends": [
            {
                "title": t.title,
                "source": t.source,
                "url": t.url,
                "summary": t.summary,
                "category": t.category,
                "relevance_score": t.relevance_score,
                "actionable": t.actionable,
                "discovered_at": t.discovered_at,
            }
            for t in filtered[:50]
        ],
        "total": len(filtered),
        "scrape_time_ms": round((time.time() - start) * 1000, 2),
    }


@app.post("/api/run")
async def trigger_run(x_api_key: str | None = Header(default=None)) -> Dict[str, Any]:
    """Trigger an R&D cycle manually. Requires API key if DASHBOARD_API_KEY is set."""
    global _last_run_time
    
    # API key authentication (if configured)
    if DASHBOARD_API_KEY and x_api_key != DASHBOARD_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Rate limiting
    elapsed = time.time() - _last_run_time
    if elapsed < _RATE_LIMIT_COOLDOWN:
        remaining = int(_RATE_LIMIT_COOLDOWN - elapsed)
        raise HTTPException(status_code=429, detail=f"Please wait {remaining} seconds before running again")
    
    _last_run_time = time.time()
    proc = subprocess.Popen([sys.executable, str(BASE_DIR / "rd_system.py"), "--force"])
    return {"message": "R&D cycle started", "pid": proc.pid}

if __name__ == "__main__":
    uvicorn.run("rd_api:app", host="0.0.0.0", port=8003, reload=True)
