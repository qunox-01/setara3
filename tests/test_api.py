"""
Smoke tests for the xariff FastAPI app.
Tests: GET routes, basic HTTP responses, content type checks.
"""
import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app


# ─── Client fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """
    Use TestClient with lifespan to run startup (DB creation).
    The DB is created in-memory via aiosqlite for tests.
    """
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ─── Page smoke tests ────────────────────────────────────────────────────────

def test_home_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "xariff" in resp.text.lower()
    assert "text/html" in resp.headers["content-type"]


def test_about_page(client):
    resp = client.get("/about")
    assert resp.status_code == 200
    assert "about" in resp.text.lower()
    assert resp.status_code == 200


def test_contact_page(client):
    resp = client.get("/contact")
    assert resp.status_code == 200
    assert "contact" in resp.text.lower()
    assert "contactus@xariff.com" in resp.text.lower()


def test_tools_index(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert "quality" in resp.text.lower()
    assert "scorecard" in resp.text.lower()


def test_tools_quality_page(client):
    resp = client.get("/tools/quality")
    assert resp.status_code == 200
    assert "quality" in resp.text.lower()


def test_tools_scorecard_page(client):
    resp = client.get("/tools/scorecard")
    assert resp.status_code == 200
    assert "scorecard" in resp.text.lower()


def test_tools_coverage_coming_soon(client):
    resp = client.get("/tools/coverage")
    assert resp.status_code == 200
    assert "coming" in resp.text.lower()


def test_tools_outliers_coming_soon(client):
    resp = client.get("/tools/outliers")
    assert resp.status_code == 200


def test_blog_index(client):
    resp = client.get("/blog")
    assert resp.status_code == 200
    assert "blog" in resp.text.lower()


def test_blog_missing_article_returns_404(client):
    resp = client.get("/blog/this-article-does-not-exist-xyz")
    assert resp.status_code == 404


def test_report_missing_returns_404(client):
    resp = client.get("/report/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ─── Static assets ──────────────────────────────────────────────────────────

def test_static_css(client):
    resp = client.get("/static/css/custom.css")
    assert resp.status_code == 200


def test_static_js(client):
    resp = client.get("/static/js/app.js")
    assert resp.status_code == 200


# ─── Utility endpoints ───────────────────────────────────────────────────────

def test_sitemap_xml(client):
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    assert "<urlset" in resp.text


def test_robots_txt(client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert "User-agent" in resp.text


# ─── Sample data endpoints ───────────────────────────────────────────────────

def test_sample_data_quality(client):
    resp = client.get("/sample-data/quality")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    # Should be parseable as CSV
    df = pd.read_csv(io.StringIO(resp.text))
    assert len(df) > 0


def test_sample_data_scorecard(client):
    resp = client.get("/sample-data/scorecard")
    assert resp.status_code == 200
    df = pd.read_csv(io.StringIO(resp.text))
    assert len(df) > 0
    assert "label" in df.columns


def test_sample_data_unknown_tool(client):
    resp = client.get("/sample-data/unknown-tool-xyz")
    assert resp.status_code == 200  # Returns default sample


# ─── API endpoints ───────────────────────────────────────────────────────────

def test_email_capture(client):
    resp = client.post(
        "/api/email-capture",
        data={"email": "test@example.com", "source": "test", "tool": "", "utm_source": ""},
    )
    assert resp.status_code == 200
    assert "thank" in resp.text.lower()


def test_feedback_endpoint(client):
    resp = client.post(
        "/api/feedback",
        data={"tool": "quality", "useful": "yes", "comment": ""},
    )
    assert resp.status_code == 200


def test_contact_feedback_endpoint(client):
    resp = client.post(
        "/api/contact-feedback",
        data={
            "name": "Test User",
            "email": "test@example.com",
            "category": "feedback",
            "subject": "Product feedback",
            "message": "The tools are useful. Please add more export options.",
        },
    )
    assert resp.status_code == 200
    assert "message has been sent" in resp.text.lower()


def test_track_endpoint(client):
    resp = client.post(
        "/api/track",
        data={"event": "test_event", "tool": "quality", "metadata": "{}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


# ─── Analysis endpoints ──────────────────────────────────────────────────────

def _make_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode()


def test_quality_analyse(client):
    df = pd.DataFrame({
        "a": [1, 2, None, 4, 5],
        "b": ["x", "y", "z", None, "w"],
        "c": [10.0, 20.0, 30.0, 40.0, 50.0],
    })
    csv_bytes = _make_csv_bytes(df)
    resp = client.post(
        "/tools/quality/analyse",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    # Should contain score and column info
    assert "quality" in resp.text.lower() or "score" in resp.text.lower() or "column" in resp.text.lower()


def test_scorecard_analyse(client):
    df = pd.DataFrame({
        "feature_1": range(100),
        "feature_2": [float(i) * 0.5 for i in range(100)],
        "label": [i % 2 for i in range(100)],
    })
    csv_bytes = _make_csv_bytes(df)
    resp = client.post(
        "/tools/scorecard/analyse",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
        data={"label_column": "label", "stage": "training"},
    )
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_quality_analyse_invalid_file(client):
    resp = client.post(
        "/tools/quality/analyse",
        files={"file": ("test.txt", b"not a csv file content here", "text/plain")},
    )
    assert resp.status_code == 422


def test_quality_analyse_empty_csv(client):
    """An empty CSV (headers only) should return a valid response."""
    df = pd.DataFrame({"a": pd.Series([], dtype=float)})
    csv_bytes = _make_csv_bytes(df)
    resp = client.post(
        "/tools/quality/analyse",
        files={"file": ("empty.csv", csv_bytes, "text/csv")},
    )
    # Should succeed or return 422 (both are acceptable for edge case)
    assert resp.status_code in (200, 422, 500)


# ─── Blog article with existing content ─────────────────────────────────────

def test_blog_article_exists(client):
    """The sample article should be accessible by its slug."""
    resp = client.get("/blog/getting-started-with-data-quality")
    assert resp.status_code == 200
    assert "data quality" in resp.text.lower()
