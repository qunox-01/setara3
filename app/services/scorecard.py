from __future__ import annotations

import pandas as pd

from app.services import quality as quality_service


def _check_class_balance(df: pd.DataFrame, label_column: str | None) -> dict:
    if not label_column or label_column not in df.columns:
        return {
            "name": "Class Balance",
            "score": 50,
            "status": "warning",
            "details": "No label column specified. Cannot evaluate class balance.",
        }

    counts = df[label_column].value_counts(normalize=True)
    if len(counts) == 0:
        return {
            "name": "Class Balance",
            "score": 0,
            "status": "critical",
            "details": "Label column is empty.",
        }

    min_ratio = float(counts.min())
    max_ratio = float(counts.max())
    imbalance_ratio = max_ratio / max(min_ratio, 1e-9)

    if imbalance_ratio < 2:
        score, status = 95, "ok"
        details = f"Well balanced. Imbalance ratio: {imbalance_ratio:.1f}x"
    elif imbalance_ratio < 5:
        score, status = 70, "warning"
        details = f"Moderate imbalance. Ratio: {imbalance_ratio:.1f}x. Consider oversampling."
    elif imbalance_ratio < 20:
        score, status = 40, "warning"
        details = f"Significant imbalance. Ratio: {imbalance_ratio:.1f}x. Strongly consider resampling."
    else:
        score, status = 15, "critical"
        details = f"Severe imbalance. Ratio: {imbalance_ratio:.1f}x. Model will likely be biased."

    return {"name": "Class Balance", "score": score, "status": status, "details": details}


def _check_completeness(df: pd.DataFrame) -> dict:
    total_cells = df.size
    if total_cells == 0:
        return {"name": "Completeness", "score": 0, "status": "critical", "details": "Empty dataset."}

    missing_cells = int(df.isna().sum().sum())
    completeness_pct = (1 - missing_cells / total_cells) * 100

    if completeness_pct >= 98:
        score, status = 100, "ok"
    elif completeness_pct >= 90:
        score, status = 80, "ok"
    elif completeness_pct >= 75:
        score, status = 60, "warning"
    elif completeness_pct >= 50:
        score, status = 30, "warning"
    else:
        score, status = 10, "critical"

    return {
        "name": "Completeness",
        "score": score,
        "status": status,
        "details": f"{completeness_pct:.1f}% cells complete. {missing_cells:,} missing values.",
    }


def _check_volume(df: pd.DataFrame, stage: str) -> dict:
    n_rows = len(df)
    thresholds = {
        "exploration": {"ok": 100, "warning": 50},
        "training": {"ok": 1000, "warning": 500},
        "production": {"ok": 5000, "warning": 1000},
    }
    t = thresholds.get(stage, thresholds["exploration"])

    if n_rows >= t["ok"]:
        score, status = 90, "ok"
        details = f"{n_rows:,} rows. Sufficient for {stage} stage."
    elif n_rows >= t["warning"]:
        score, status = 60, "warning"
        details = f"{n_rows:,} rows. Borderline for {stage} stage. More data recommended."
    else:
        score, status = 20, "critical"
        details = f"Only {n_rows:,} rows. Too few for {stage} stage (need {t['ok']:,}+)."

    return {"name": "Data Volume", "score": score, "status": status, "details": details}


def _check_uniqueness(df: pd.DataFrame) -> dict:
    if len(df) == 0:
        return {"name": "Uniqueness", "score": 0, "status": "critical", "details": "Empty dataset."}

    dup_count = int(df.duplicated().sum())
    dup_pct = dup_count / len(df) * 100

    if dup_pct < 1:
        score, status = 100, "ok"
    elif dup_pct < 5:
        score, status = 80, "ok"
    elif dup_pct < 15:
        score, status = 55, "warning"
    elif dup_pct < 30:
        score, status = 30, "warning"
    else:
        score, status = 10, "critical"

    return {
        "name": "Uniqueness",
        "score": score,
        "status": status,
        "details": f"{dup_count:,} duplicate rows ({dup_pct:.1f}%).",
    }


def _generate_recommendations(dimensions: list[dict]) -> list[dict]:
    recommendations = []
    for dim in dimensions:
        if dim["status"] == "critical":
            priority = "high"
        elif dim["status"] == "warning":
            priority = "medium"
        else:
            continue

        msg_map = {
            "Class Balance": "Address class imbalance using SMOTE, undersampling, or class weights.",
            "Completeness": "Impute or remove missing values. Consider median/mode imputation for numeric/categorical columns.",
            "Data Volume": "Collect more data or use data augmentation techniques.",
            "Uniqueness": "Remove duplicate rows before training to prevent data leakage.",
        }
        message = msg_map.get(dim["name"], f"Review {dim['name']}: {dim['details']}")
        recommendations.append({"priority": priority, "message": message, "dimension": dim["name"]})

    return recommendations


def analyse(df: pd.DataFrame, label_column: str | None, stage: str) -> dict:
    quality_result = quality_service.analyse(df)
    quality_score = quality_result["summary"]["overall_score"]

    quality_dim = {
        "name": "Data Quality",
        "score": quality_score,
        "status": quality_result["summary"]["verdict"].lower().replace(" ", "_"),
        "details": (
            f"Overall quality score: {quality_score}/100. "
            f"Verdict: {quality_result['summary']['verdict']}."
        ),
    }
    # Normalise status
    if quality_dim["status"] == "healthy":
        quality_dim["status"] = "ok"
    elif quality_dim["status"] == "needs_attention":
        quality_dim["status"] = "warning"

    dimensions = [
        quality_dim,
        _check_completeness(df),
        _check_class_balance(df, label_column),
        _check_volume(df, stage),
        _check_uniqueness(df),
    ]

    overall_score = int(sum(d["score"] for d in dimensions) / len(dimensions))

    if overall_score >= 80:
        verdict = "Ready for ML"
    elif overall_score >= 55:
        verdict = "Needs improvement"
    else:
        verdict = "Not ready — critical issues found"

    recommendations = _generate_recommendations(dimensions)

    return {
        "overall_score": overall_score,
        "verdict": verdict,
        "dimensions": dimensions,
        "recommendations": recommendations,
        "stage": stage,
        "label_column": label_column or "N/A",
    }
