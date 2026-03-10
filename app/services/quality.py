from __future__ import annotations

import numpy as np
import pandas as pd


def _detect_mixed_types(series: pd.Series) -> bool:
    """Return True if series has mixed numeric and non-numeric values in an object column."""
    if series.dtype != object:
        return False
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    numeric_count = pd.to_numeric(non_null, errors="coerce").notna().sum()
    return 0 < numeric_count < len(non_null)


def _count_outliers_iqr(series: pd.Series) -> int:
    """Count outliers using IQR method for numeric columns."""
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric) < 4:
        return 0
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return int(((numeric < lower) | (numeric > upper)).sum())


def _column_status(missing_pct: float, outlier_count: int, mixed_types: bool, total_rows: int) -> str:
    if missing_pct > 50 or mixed_types:
        return "critical"
    if missing_pct > 20 or (total_rows > 0 and outlier_count / max(total_rows, 1) > 0.10):
        return "warning"
    return "ok"


def analyse(df: pd.DataFrame) -> dict:
    total_rows, total_columns = df.shape
    memory_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 3)

    dup_mask = df.duplicated(keep=False)
    total_duplicates = int(dup_mask.sum())

    columns_info = []
    penalty = 0.0

    for col in df.columns:
        series = df[col]
        missing_count = int(series.isna().sum())
        missing_pct = round(missing_count / total_rows * 100, 2) if total_rows > 0 else 0.0
        dup_count = int(dup_mask.sum())  # row-level, reused as approximation
        mixed = _detect_mixed_types(series)
        outlier_count = _count_outliers_iqr(series)
        status = _column_status(missing_pct, outlier_count, mixed, total_rows)

        columns_info.append(
            {
                "name": col,
                "dtype": str(series.dtype),
                "missing_count": missing_count,
                "missing_pct": missing_pct,
                "duplicate_count": total_duplicates,
                "mixed_types": mixed,
                "outlier_count": outlier_count,
                "status": status,
            }
        )

        # Weighted penalties
        if status == "critical":
            penalty += 15
        elif status == "warning":
            penalty += 5
        elif missing_pct > 5:
            penalty += 2

    # Global duplicate penalty
    if total_rows > 0:
        dup_pct = total_duplicates / total_rows * 100
        if dup_pct > 20:
            penalty += 20
        elif dup_pct > 5:
            penalty += 10

    # Cap penalty
    overall_score = max(0, int(100 - penalty))

    if overall_score >= 80:
        verdict = "Healthy"
    elif overall_score >= 50:
        verdict = "Needs attention"
    else:
        verdict = "Critical"

    # Flagged rows: missing any value OR duplicated
    flagged_mask = df.isna().any(axis=1) | dup_mask
    flagged_rows = df[flagged_mask].head(100).to_dict(orient="records")

    return {
        "summary": {
            "total_rows": total_rows,
            "total_columns": total_columns,
            "memory_mb": memory_mb,
            "overall_score": overall_score,
            "verdict": verdict,
            "total_duplicates": total_duplicates,
        },
        "columns": columns_info,
        "flagged_rows": flagged_rows,
        "flagged_count": int(flagged_mask.sum()),
    }
