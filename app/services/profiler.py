from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

SAMPLE_THRESHOLD = 100_000
MAX_ROWS_BEFORE_SAMPLE = 500_000
CATEGORICAL_MAX_UNIQUE = 50


def _col_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "categorical"
    return "categorical" if series.nunique() <= CATEGORICAL_MAX_UNIQUE else "text"


def _histogram(series: pd.Series, bins: int = 30) -> list[dict]:
    vals = pd.to_numeric(series, errors="coerce").dropna().values
    if len(vals) < 2:
        return []
    counts, edges = np.histogram(vals, bins=bins)
    return [
        {"bin_start": round(float(edges[i]), 6), "bin_end": round(float(edges[i + 1]), 6), "count": int(counts[i])}
        for i in range(len(counts))
    ]


def _boxplot(series: pd.Series) -> dict | None:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    if len(vals) < 4:
        return None
    q1 = float(vals.quantile(0.25))
    med = float(vals.median())
    q3 = float(vals.quantile(0.75))
    iqr = q3 - q1
    w_lo = float(max(vals.min(), q1 - 1.5 * iqr))
    w_hi = float(min(vals.max(), q3 + 1.5 * iqr))
    return {
        "q1": round(q1, 6),
        "median": round(med, 6),
        "q3": round(q3, 6),
        "whisker_low": round(w_lo, 6),
        "whisker_high": round(w_hi, 6),
        "outlier_count": int(((vals < w_lo) | (vals > w_hi)).sum()),
    }


def _num_stats(series: pd.Series) -> dict:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    if len(vals) == 0:
        return {}
    q1 = float(vals.quantile(0.25))
    q3 = float(vals.quantile(0.75))
    skew, kurt = None, None
    if len(vals) >= 3:
        try:
            s = float(scipy_stats.skew(vals))
            k = float(scipy_stats.kurtosis(vals))
            if not pd.isna(s):
                skew = round(s, 4)
            if not pd.isna(k):
                kurt = round(k, 4)
        except Exception:
            pass
    std = vals.std()
    return {
        "mean": round(float(vals.mean()), 6),
        "median": round(float(vals.median()), 6),
        "std": round(float(std), 6) if not pd.isna(std) else None,
        "min": round(float(vals.min()), 6),
        "max": round(float(vals.max()), 6),
        "q1": round(q1, 6),
        "q3": round(q3, 6),
        "iqr": round(q3 - q1, 6),
        "skewness": skew,
        "kurtosis": kurt,
    }


def _top_values(series: pd.Series, n: int = 10) -> list[dict]:
    total = len(series)
    counts = series.value_counts(dropna=True)
    result = [
        {"value": str(k), "count": int(v), "pct": round(v / total * 100, 2) if total else 0.0}
        for k, v in counts.head(n).items()
    ]
    if len(counts) > n:
        other = int(counts.iloc[n:].sum())
        result.append({"value": "Other", "count": other, "pct": round(other / total * 100, 2) if total else 0.0})
    return result


def _cat_stats(series: pd.Series) -> dict:
    non_null = series.dropna()
    modes = non_null.mode()
    return {"mode": str(modes.iloc[0]) if len(modes) else None}


def _dt_stats(series: pd.Series) -> dict:
    try:
        dt = pd.to_datetime(series.dropna(), errors="coerce").dropna()
        if len(dt) == 0:
            return {}
        return {
            "min_date": str(dt.min().date()),
            "max_date": str(dt.max().date()),
            "date_range_days": int((dt.max() - dt.min()).days),
        }
    except Exception:
        return {}


def _text_stats(series: pd.Series) -> dict:
    lengths = series.dropna().astype(str).str.len()
    if len(lengths) == 0:
        return {}
    return {
        "avg_length": round(float(lengths.mean()), 2),
        "min_length": int(lengths.min()),
        "max_length": int(lengths.max()),
    }


def compute_profile(df: pd.DataFrame) -> dict:
    original_rows = len(df)
    sampled = original_rows > MAX_ROWS_BEFORE_SAMPLE
    if sampled:
        df = df.sample(n=SAMPLE_THRESHOLD, random_state=42)

    rows, cols = df.shape
    missing_total = int(df.isna().sum().sum())
    total_cells = rows * cols
    dup_rows = int(df.duplicated().sum())

    features = []
    for col in df.columns:
        s = df[col]
        ctype = _col_type(s)
        mc = int(s.isna().sum())
        uc = int(s.nunique())
        feature: dict = {
            "name": col,
            "dtype": str(s.dtype),
            "type": ctype,
            "missing_count": mc,
            "missing_pct": round(mc / rows * 100, 2) if rows else 0.0,
            "unique_count": uc,
            "unique_pct": round(uc / rows * 100, 2) if rows else 0.0,
            "stats": None,
            "histogram": None,
            "box_plot": None,
            "top_values": None,
        }
        if ctype == "numeric":
            feature["stats"] = _num_stats(s)
            feature["histogram"] = _histogram(s)
            feature["box_plot"] = _boxplot(s)
        elif ctype == "categorical":
            feature["stats"] = _cat_stats(s)
            feature["top_values"] = _top_values(s)
        elif ctype == "datetime":
            feature["stats"] = _dt_stats(s)
        else:
            feature["stats"] = _text_stats(s)
            feature["top_values"] = _top_values(s, n=5)
        features.append(feature)

    correlations = None
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if 2 <= len(num_cols) <= 30:
        corr = df[num_cols].corr().round(2)
        correlations = {
            "columns": num_cols,
            "matrix": [
                [None if pd.isna(v) else round(float(v), 2) for v in row]
                for row in corr.values
            ],
        }

    return {
        "dataset": {
            "rows": rows,
            "columns": cols,
            "missing_total": missing_total,
            "missing_pct": round(missing_total / total_cells * 100, 2) if total_cells else 0.0,
            "duplicate_rows": dup_rows,
            "duplicate_pct": round(dup_rows / rows * 100, 2) if rows else 0.0,
            "memory_bytes": int(df.memory_usage(deep=True).sum()),
            "sampled": sampled,
            "original_rows": original_rows if sampled else None,
        },
        "features": features,
        "correlations": correlations,
    }
