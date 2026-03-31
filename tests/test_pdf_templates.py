import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.services import coverage, drift, outliers, profiler, quality, scorecard


env = Environment(loader=FileSystemLoader("templates"), undefined=StrictUndefined)


def _render(template_name: str, result: dict) -> str:
    template = env.get_template(template_name)
    return template.render(result=result, generated_at="March 31, 2026")


def test_quality_pdf_renders():
    df = pd.DataFrame({
        "a": [1, 2, None, 2],
        "b": ["x", "y", "y", None],
        "c": [1.0, 100.0, 3.0, 4.0],
    })
    html = _render("pdf/quality_pdf.html", quality.analyse(df))
    assert "Data Quality Report" in html


def test_scorecard_pdf_renders():
    df = pd.DataFrame({
        "feature_1": range(20),
        "feature_2": [float(i) * 0.5 for i in range(20)],
        "label": [i % 2 for i in range(20)],
    })
    html = _render(
        "pdf/scorecard_pdf.html",
        scorecard.analyse(df, label_column="label", stage="training"),
    )
    assert "ML Readiness Scorecard" in html


def test_profiler_pdf_renders():
    df = pd.DataFrame({
        "num": [1, 2, 3, 4, 5],
        "cat": ["a", "b", "a", "c", "b"],
        "txt": ["one", "two", "three", None, "five"],
    })
    html = _render("pdf/profiler_pdf.html", profiler.compute_profile(df))
    assert "Dataset Profile Report" in html


def test_outliers_pdf_renders():
    df = pd.DataFrame({
        "x": [1, 2, 3, 100, 5, 6, 7, 8, 9, 10, 11, 12],
        "y": [1, 2, 3, 100, 5, 6, 7, 8, 9, 10, 11, 12],
        "label": ["a"] * 12,
    })
    html = _render("pdf/outliers_pdf.html", outliers.analyse(df, method="ensemble", label_col="label"))
    assert "Outlier Detection Report" in html


def test_coverage_pdf_renders():
    df = pd.DataFrame({
        "f1": range(60),
        "f2": [v * 2 for v in range(60)],
        "f3": [v % 7 for v in range(60)],
    })
    html = _render("pdf/coverage_pdf.html", coverage.analyse(df))
    assert "Feature-Space Coverage Report" in html


def test_drift_pdf_renders():
    ref = pd.DataFrame({
        "n": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "c": ["a", "a", "b", "b", "c", "c", "a", "b", "c", "a"],
    })
    cur = pd.DataFrame({
        "n": [2, 3, 4, 5, 6, 7, 8, 9, 10, 20],
        "c": ["a", "b", "b", "b", "c", "c", "c", "b", "c", "c"],
    })
    html = _render("pdf/drift_pdf.html", drift.analyse(ref, cur))
    assert "Dataset Drift Report" in html
