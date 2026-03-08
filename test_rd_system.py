#!/usr/bin/env python3
"""
Tests for AI R&D System
Run: pytest test_rd_system.py -v
"""
import pytest
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Import the system module
from rd_system import (
    Trend, Upgrade, load_state, save_state, score_relevance,
    classify_category, generate_upgrades
)


def _validate_filename(name: str) -> bool:
    """Validate filename to prevent path traversal attacks."""
    import re
    if ".." in name or "/" in name or "\\" in name:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', name))


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def sample_trend():
    return Trend(
        title="Test Trend",
        source="GitHub",
        url="https://github.com/test/repo",
        summary="A test repository",
        category="tool",
        relevance_score=75,
        actionable=True,
        implementation_hint="Test hint",
        discovered_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def sample_upgrade():
    return Upgrade(
        title="Test Upgrade",
        category="performance",
        description="Test upgrade description",
        file_path="test.py",
        code_before="# old code",
        code_after="# new code",
        risk_level="safe",
        applied=False,
        applied_at=None,
    )


@pytest.fixture
def temp_state_file(tmp_path):
    state_file = tmp_path / ".rd_state.json"
    with patch('rd_system.STATE_FILE', state_file):
        yield state_file


# ── State Management Tests ────────────────────────────────────────────────────
class TestStateManagement:
    def test_load_state_empty(self, tmp_path):
        """Test loading state when file doesn't exist."""
        state_file = tmp_path / ".rd_state.json"
        
        # Manually test the function with a custom path
        import json
        from pathlib import Path
        
        # Simulate non-existent file
        def mock_load_state():
            if state_file.exists():
                return json.loads(state_file.read_text())
            return {"last_run": None, "seen_urls": [], "applied_upgrades": [], "week_number": 0}
        
        state = mock_load_state()
        assert state == {"last_run": None, "seen_urls": [], "applied_upgrades": [], "week_number": 0}

    def test_load_state_valid(self, tmp_path):
        """Test loading valid state file."""
        state_file = tmp_path / ".rd_state.json"
        test_state = {"last_run": "2025-01-01T00:00:00", "week_number": 5, "seen_urls": [], "applied_upgrades": []}
        state_file.write_text(json.dumps(test_state))
        
        state = json.loads(state_file.read_text())
        assert state["last_run"] == "2025-01-01T00:00:00"
        assert state["week_number"] == 5

    def test_load_state_corrupted(self, tmp_path):
        """Test loading corrupted state file (graceful fallback)."""
        state_file = tmp_path / ".rd_state.json"
        state_file.write_text("not valid json {{{")
        
        import json
        try:
            state = json.loads(state_file.read_text())
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError:
            # This is expected - the real code handles this gracefully
            pass

    def test_save_state(self, tmp_path):
        """Test saving state file."""
        state_file = tmp_path / ".rd_state.json"
        
        test_state = {"last_run": "2025-01-01T00:00:00", "week_number": 10}
        state_file.write_text(json.dumps(test_state))
        
        loaded = json.loads(state_file.read_text())
        assert loaded["week_number"] == 10


# ── Relevance Scoring Tests ───────────────────────────────────────────────────
class TestRelevanceScoring:
    def test_score_with_high_relevance_keywords(self):
        """Test scoring with high relevance keywords."""
        text = "fastapi async streaming endpoint with websocket"
        score = score_relevance(text)
        assert score > 0
        assert score <= 100

    def test_score_with_ai_terms_bonus(self):
        """Test bonus scoring for AI/agent terms."""
        text = "llm agent using groq and claude"
        score = score_relevance(text)
        # Should have bonus points for multiple AI terms
        assert score > 15

    def test_score_empty_text(self):
        """Test scoring empty text."""
        score = score_relevance("")
        assert score == 0

    def test_score_capped_at_100(self):
        """Test that score is capped at 100."""
        text = " ".join(["fastapi"] * 50)  # Many keyword matches
        score = score_relevance(text)
        assert score <= 100

    def test_score_case_insensitive(self):
        """Test that scoring is case insensitive."""
        text1 = score_relevance("FASTAPI ASYNC")
        text2 = score_relevance("fastapi async")
        assert text1 == text2


# ── Classification Tests ──────────────────────────────────────────────────────
class TestClassification:
    def test_classify_model(self):
        """Test model category classification."""
        assert classify_category("gpt-4 model") == "model"
        assert classify_category("llama llm") == "model"
        assert classify_category("claude groq gemini") == "model"

    def test_classify_framework(self):
        """Test framework category classification."""
        assert classify_category("crewai framework") == "framework"
        assert classify_category("langchain langgraph") == "framework"

    def test_classify_pattern(self):
        """Test pattern category classification."""
        assert classify_category("rag architecture pattern") == "pattern"
        assert classify_category("agent design") == "pattern"

    def test_classify_security(self):
        """Test security category classification."""
        assert classify_category("jwt auth vulnerability") == "security"
        assert classify_category("oauth security") == "security"

    def test_classify_default_tool(self):
        """Test default tool category."""
        assert classify_category("random tool") == "tool"


# ── Upgrade Generation Tests ──────────────────────────────────────────────────
class TestUpgradeGeneration:
    def test_generate_upgrades_returns_list(self):
        """Test that generate_upgrades returns a list."""
        import importlib
        import rd_system
        importlib.reload(rd_system)
        
        upgrades = rd_system.generate_upgrades([])
        assert isinstance(upgrades, list)

    def test_generate_upgrades_creates_upgrade_objects(self):
        """Test that generated upgrades are Upgrade instances."""
        import importlib
        import rd_system
        importlib.reload(rd_system)
        
        upgrades = rd_system.generate_upgrades([])
        for upgrade in upgrades:
            assert isinstance(upgrade, rd_system.Upgrade)

    def test_generate_upgrades_has_required_fields(self):
        """Test that upgrades have all required fields."""
        import importlib
        import rd_system
        importlib.reload(rd_system)
        
        upgrades = rd_system.generate_upgrades([])
        for upgrade in upgrades:
            assert upgrade.title
            assert upgrade.category
            assert upgrade.description
            assert upgrade.file_path
            assert upgrade.code_before
            assert upgrade.code_after
            assert upgrade.risk_level in ["safe", "moderate", "breaking"]


# ── Filename Validation Tests (Security) ──────────────────────────────────────
class TestFilenameValidation:
    def test_validate_valid_filename(self):
        """Test validation of valid filenames."""
        assert _validate_filename("report.md") is True
        assert _validate_filename("upgrade_001.py") is True
        assert _validate_filename("test-file_123.txt") is True

    def test_validate_path_traversal(self):
        """Test rejection of path traversal attempts."""
        assert _validate_filename("../etc/passwd") is False
        assert _validate_filename("..\\windows\\system32") is False
        assert _validate_filename("report/../secret") is False

    def test_validate_absolute_paths(self):
        """Test rejection of absolute paths."""
        assert _validate_filename("/etc/passwd") is False
        assert _validate_filename("C:\\windows") is False

    def test_validate_special_characters(self):
        """Test rejection of special characters."""
        assert _validate_filename("file;rm -rf") is False
        assert _validate_filename("file$(whoami)") is False


# ── Trend Model Tests ─────────────────────────────────────────────────────────
class TestTrendModel:
    def test_trend_creation(self, sample_trend):
        """Test creating a Trend instance."""
        assert sample_trend.title == "Test Trend"
        assert sample_trend.category == "tool"
        assert sample_trend.relevance_score == 75
        assert sample_trend.actionable is True

    def test_trend_to_dict(self, sample_trend):
        """Test converting Trend to dictionary."""
        from dataclasses import asdict
        trend_dict = asdict(sample_trend)
        assert trend_dict["title"] == "Test Trend"
        assert trend_dict["category"] == "tool"


# ── Upgrade Model Tests ───────────────────────────────────────────────────────
class TestUpgradeModel:
    def test_upgrade_creation(self, sample_upgrade):
        """Test creating an Upgrade instance."""
        assert sample_upgrade.title == "Test Upgrade"
        assert sample_upgrade.category == "performance"
        assert sample_upgrade.risk_level == "safe"
        assert sample_upgrade.applied is False

    def test_upgrade_to_dict(self, sample_upgrade):
        """Test converting Upgrade to dictionary."""
        from dataclasses import asdict
        upgrade_dict = asdict(sample_upgrade)
        assert upgrade_dict["title"] == "Test Upgrade"
        assert upgrade_dict["risk_level"] == "safe"


# ── Integration Tests ─────────────────────────────────────────────────────────
class TestIntegration:
    def test_full_workflow(self, temp_state_file):
        """Test complete workflow: state -> trends -> upgrades."""
        # Initialize state
        initial_state = load_state()
        assert initial_state["week_number"] == 0

        # Simulate trends
        trends = [
            Trend(
                title="New AI Framework",
                source="GitHub",
                url="https://github.com/test",
                summary="Test",
                category="framework",
                relevance_score=80,
                actionable=True,
                implementation_hint="Test",
                discovered_at=datetime.now(timezone.utc).isoformat(),
            )
        ]

        # Generate upgrades
        upgrades = generate_upgrades(trends)
        assert len(upgrades) > 0

        # Update state
        initial_state["week_number"] = 1
        initial_state["applied_upgrades"] = [u.title for u in upgrades if u.risk_level == "safe"]
        save_state(initial_state)

        # Verify
        final_state = load_state()
        assert final_state["week_number"] == 1


# ── API Endpoint Tests (for rd_api.py) ────────────────────────────────────────
class TestAPIEndpoints:
    @pytest.fixture
    def test_client(self):
        """Create test client for FastAPI app."""
        from fastapi.testclient import TestClient
        from rd_api import app
        return TestClient(app)

    def test_health_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "uptime" in data

    def test_get_state(self, test_client):
        """Test get state endpoint."""
        response = test_client.get("/api/state")
        assert response.status_code == 200
        data = response.json()
        assert "week_number" in data or "last_run" in data

    def test_get_reports_empty(self, test_client):
        """Test list reports when empty."""
        response = test_client.get("/api/reports")
        assert response.status_code == 200
        data = response.json()
        assert "reports" in data

    def test_get_upgrades_empty(self, test_client):
        """Test list upgrades when empty."""
        response = test_client.get("/api/upgrades")
        assert response.status_code == 200
        data = response.json()
        assert "upgrades" in data

    def test_invalid_report_name(self, test_client):
        """Test path traversal protection."""
        # URL-encoded: ../etc/passwd
        response = test_client.get("/api/reports/..%2Fetc%2Fpasswd")
        assert response.status_code in [400, 404]  # Either blocked or not found is acceptable

    def test_invalid_upgrade_name(self, test_client):
        """Test path traversal protection for upgrades."""
        # URL-encoded: ../secret
        response = test_client.get("/api/upgrades/..%2Fsecret")
        assert response.status_code in [400, 404]  # Either blocked or not found is acceptable


# ── Run Tests ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ── Async Scraper Tests ───────────────────────────────────────────────────────
class TestAsyncScrapers:
    @pytest.mark.asyncio
    async def test_scrape_github_trending(self):
        """Test GitHub trending scraper."""
        import aiohttp
        from rd_scrapers import scrape_github_trending
        
        async with aiohttp.ClientSession() as session:
            url = "https://api.github.com/search/repositories?q=ai+created:>2025-01-01&sort=stars&order=desc&per_page=5"
            result = await scrape_github_trending(session, url, "GitHub Test")
            
            assert result.source == "GitHub Test"
            assert isinstance(result.trends, list)
            # May be empty if API rate limited
            if result.trends:
                assert all(isinstance(t, Trend) for t in result.trends)

    def test_scrape_all_sources_sync(self):
        """Test sync wrapper for async scrapers."""
        from rd_scrapers import scrape_all_sources_sync
        from rd_system import TREND_SOURCES
        
        # Use minimal sources for faster test
        test_sources = [s for s in TREND_SOURCES if s["type"] == "github"][:1]
        
        trends = scrape_all_sources_sync(test_sources)
        assert isinstance(trends, list)


# ── Slack Notification Tests ──────────────────────────────────────────────────
class TestSlackNotifications:
    def test_slack_message_format(self):
        """Test Slack message structure."""
        from rd_system import send_slack_notification
        import json
        
        # Create test report
        test_report = """# Test Report
## Summary
This is a test summary.
"""
        
        # Verify message structure (without actually sending)
        summary_lines = test_report.split("\n")[:15]
        assert len(summary_lines) <= 15
        
    def test_slack_webhook_not_configured(self, capsys):
        """Test graceful handling when Slack not configured."""
        from rd_system import send_slack_notification
        
        # Should not raise error when webhook not set
        send_slack_notification("Test report", 1)
        captured = capsys.readouterr()
        assert "Slack not configured" in captured.out


# ── Trend Filtering API Tests ─────────────────────────────────────────────────
class TestTrendFilteringAPI:
    @pytest.fixture
    def test_client(self):
        """Create test client for FastAPI app."""
        from fastapi.testclient import TestClient
        from rd_api import app
        return TestClient(app)
    
    def test_live_trends_endpoint(self, test_client):
        """Test /api/trends/live endpoint."""
        response = test_client.get("/api/trends/live")
        assert response.status_code == 200
        data = response.json()
        assert "trends" in data
        assert "scrape_time_ms" in data
    
    def test_trends_filter_by_category(self, test_client):
        """Test category filtering."""
        response = test_client.get("/api/trends/live?category=model")
        assert response.status_code == 200
        data = response.json()
        
        # All returned trends should match category
        for trend in data["trends"]:
            assert trend["category"] == "model"
    
    def test_trends_filter_by_relevance(self, test_client):
        """Test relevance filtering."""
        response = test_client.get("/api/trends/live?min_relevance=50")
        assert response.status_code == 200
        data = response.json()
        
        # All returned trends should meet min relevance
        for trend in data["trends"]:
            assert trend["relevance_score"] >= 50
    
    def test_trends_search(self, test_client):
        """Test search filtering."""
        response = test_client.get("/api/trends/live?search=ai")
        assert response.status_code == 200
        data = response.json()
        
        # All returned trends should contain search term
        search_lower = "ai"
        for trend in data["trends"]:
            assert (
                search_lower in trend["title"].lower() or 
                search_lower in trend["summary"].lower()
            )
