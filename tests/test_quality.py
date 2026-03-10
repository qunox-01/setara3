"""
Tests for app.services.quality.analyse()
"""
import numpy as np
import pandas as pd
import pytest

from app.services.quality import analyse


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def clean_df():
    """A small, clean DataFrame with no issues."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Carol", "Dave", "Eve"],
        "age": [25, 30, 35, 40, 45],
        "score": [0.9, 0.8, 0.75, 0.85, 0.95],
    })


@pytest.fixture
def dirty_df():
    """A DataFrame with missing values, outliers, and duplicates."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5, 6],
        "age": [25, None, 30, 999, 35, 25],     # missing + outlier
        "name": [None, "Bob", "Carol", "Dave", "Eve", None],   # 2 missing
        "score": [0.9, 0.8, 0.75, 0.85, 0.95, 0.9],
    })
    # Add duplicate row (row 0 == row 5 in original terms after concat)
    duplicate_row = pd.DataFrame([{"id": 1, "age": 25, "name": None, "score": 0.9}])
    return pd.concat([df, duplicate_row], ignore_index=True)


@pytest.fixture
def mixed_types_df():
    """A DataFrame with a mixed-type column."""
    return pd.DataFrame({
        "value": ["10", "20", "not_a_number", "40", "50"],
    })


@pytest.fixture
def empty_df():
    """An empty DataFrame."""
    return pd.DataFrame({"a": pd.Series([], dtype=float), "b": pd.Series([], dtype=object)})


# ─── Result structure tests ─────────────────────────────────────────────────

def test_analyse_returns_required_keys(clean_df):
    result = analyse(clean_df)
    assert "summary" in result
    assert "columns" in result
    assert "flagged_rows" in result
    assert "flagged_count" in result


def test_summary_keys(clean_df):
    summary = analyse(clean_df)["summary"]
    assert "total_rows" in summary
    assert "total_columns" in summary
    assert "memory_mb" in summary
    assert "overall_score" in summary
    assert "verdict" in summary
    assert "total_duplicates" in summary


def test_columns_list_length(clean_df):
    result = analyse(clean_df)
    assert len(result["columns"]) == len(clean_df.columns)


def test_column_keys(clean_df):
    col = analyse(clean_df)["columns"][0]
    for key in ("name", "dtype", "missing_count", "missing_pct", "duplicate_count",
                "mixed_types", "outlier_count", "status"):
        assert key in col, f"Missing key: {key}"


# ─── Clean DataFrame tests ──────────────────────────────────────────────────

def test_clean_df_high_score(clean_df):
    result = analyse(clean_df)
    assert result["summary"]["overall_score"] >= 80


def test_clean_df_verdict_healthy(clean_df):
    assert analyse(clean_df)["summary"]["verdict"] == "Healthy"


def test_clean_df_no_missing(clean_df):
    result = analyse(clean_df)
    for col in result["columns"]:
        assert col["missing_count"] == 0
        assert col["missing_pct"] == 0.0


def test_clean_df_no_flagged_rows(clean_df):
    result = analyse(clean_df)
    assert result["flagged_count"] == 0
    assert result["flagged_rows"] == []


# ─── Dirty DataFrame tests ──────────────────────────────────────────────────

def test_dirty_df_has_missing(dirty_df):
    result = analyse(dirty_df)
    age_col = next(c for c in result["columns"] if c["name"] == "age")
    assert age_col["missing_count"] >= 1


def test_dirty_df_lower_score(dirty_df, clean_df):
    dirty_score = analyse(dirty_df)["summary"]["overall_score"]
    clean_score = analyse(clean_df)["summary"]["overall_score"]
    assert dirty_score <= clean_score


def test_dirty_df_has_duplicates(dirty_df):
    result = analyse(dirty_df)
    assert result["summary"]["total_duplicates"] > 0


def test_dirty_df_has_flagged_rows(dirty_df):
    result = analyse(dirty_df)
    assert result["flagged_count"] > 0


def test_flagged_rows_max_100():
    """Flagged rows should be capped at 100."""
    large_df = pd.DataFrame({
        "a": [None] * 200,
        "b": range(200),
    })
    result = analyse(large_df)
    assert len(result["flagged_rows"]) <= 100


# ─── Mixed types test ───────────────────────────────────────────────────────

def test_mixed_types_detected(mixed_types_df):
    result = analyse(mixed_types_df)
    value_col = result["columns"][0]
    assert value_col["mixed_types"] is True


def test_mixed_types_column_status_critical(mixed_types_df):
    result = analyse(mixed_types_df)
    value_col = result["columns"][0]
    assert value_col["status"] == "critical"


# ─── Score bounds ───────────────────────────────────────────────────────────

def test_overall_score_in_range(clean_df, dirty_df):
    for df in [clean_df, dirty_df]:
        score = analyse(df)["summary"]["overall_score"]
        assert 0 <= score <= 100


# ─── Verdict values ─────────────────────────────────────────────────────────

def test_verdict_values(clean_df):
    verdict = analyse(clean_df)["summary"]["verdict"]
    assert verdict in ("Healthy", "Needs attention", "Critical")


# ─── All-null column ────────────────────────────────────────────────────────

def test_all_null_column():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [None, None, None]})
    result = analyse(df)
    b_col = next(c for c in result["columns"] if c["name"] == "b")
    assert b_col["missing_pct"] == 100.0
    assert b_col["status"] == "critical"


# ─── Single row DataFrame ────────────────────────────────────────────────────

def test_single_row_df():
    df = pd.DataFrame({"x": [42], "y": ["hello"]})
    result = analyse(df)
    assert result["summary"]["total_rows"] == 1
    assert result["summary"]["total_columns"] == 2


# ─── Memory MB is non-negative float ────────────────────────────────────────

def test_memory_mb_positive(clean_df):
    result = analyse(clean_df)
    assert result["summary"]["memory_mb"] >= 0


# ─── IQR outlier detection ───────────────────────────────────────────────────

def test_outlier_detection():
    # A column with one clear outlier
    df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 6, 7, 8, 9, 1000]})
    result = analyse(df)
    val_col = result["columns"][0]
    assert val_col["outlier_count"] >= 1
