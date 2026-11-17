import os
import sys
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.database.session import Base, get_db
from app.services.leetcode_service import clean_leetcode_html, leetcode_service

# Setup test database
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with patch("app.database.session.SessionLocal", side_effect=TestingSessionLocal):
        yield
    app.dependency_overrides.pop(get_db, None)


def test_clean_leetcode_html():
    raw_html = """
    <p>Given an array of integers <code>nums</code> and an integer <code>target</code>.</p>
    <p><strong>Example 1:</strong></p>
    <pre>
    Input: nums = [2,7,11,15], target = 9
    Output: [0,1]
    </pre>
    <ul>
      <li><code>2 &lt;= nums.length &lt;= 10<sup>4</sup></code></li>
      <li><code>-10<sup>9</sup> &lt;= nums[i] &lt;= 10<sup>9</sup></code></li>
    </ul>
    """
    cleaned = clean_leetcode_html(raw_html)
    assert "**Example 1:**" in cleaned
    assert "```" in cleaned
    assert "`nums`" in cleaned
    assert "<p>" not in cleaned
    assert "<pre>" not in cleaned


def test_leetcode_api_not_found():
    with patch.object(leetcode_service, "fetch_problem", new=AsyncMock(return_value=None)):
        resp = client.get("/api/leetcode/problem/99999999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


def test_leetcode_api_success():
    mock_problem = {
        "id": "42",
        "title": "Trapping Rain Water",
        "title_slug": "trapping-rain-water",
        "difficulty": "hard",
        "is_paid_only": False,
        "content": "Given n non-negative integers representing an elevation map...",
        "content_raw": "<p>Given n non-negative integers...</p>",
        "topic_tags": ["Array", "Two Pointers"],
        "starter_code": {"python": "class Solution:\n    def trap(self, height: list[int]) -> int:\n        pass"},
    }
    with patch.object(leetcode_service, "fetch_problem", new=AsyncMock(return_value=mock_problem)):
        resp = client.get("/api/leetcode/problem/42")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "42"
        assert data["title"] == "Trapping Rain Water"
        assert data["difficulty"] == "hard"
        assert "Array" in data["topic_tags"]


def test_session_create_with_leetcode_id_only():
    resp = client.post(
        "/api/sessions",
        json={
            "config": {
                "source": "leetcode",
                "framing": "standard",
            },
            "leetcode_id": "42",
        },
    )
    # Status code is 202 Accepted because problem generation is queued in background
    assert resp.status_code == 202
    assert "session_id" in resp.json()


def test_session_create_rejects_missing_both_id_and_statement():
    resp = client.post(
        "/api/sessions",
        json={
            "config": {
                "source": "leetcode",
                "framing": "standard",
            },
        },
    )
    assert resp.status_code == 422
    assert "requires a problem number/slug" in resp.json()["detail"]
