"""
Dataset Drift Detection Service
Compares a reference dataset against a current dataset to detect distribution shift.

Methods:
  KS Test  — Kolmogorov-Smirnov two-sample test for numeric features.
             Measures the maximum absolute difference between two CDFs.
             Flags drift when p-value < 0.05.

  PSI      — Population Stability Index.
             PSI = Σ (cur% − ref%) × ln(cur% / ref%)
             < 0.10  → No significant drift
             0.10–0.20 → Moderate drift
             ≥ 0.20  → Significant drift

Pipeline:
  1. Align common columns between reference and current datasets.
  2. For each numeric column: run KS test + compute PSI (bin by reference quantiles).
  3. For each categorical column: compute PSI (bin by reference categories).
  4. Summarise per-feature drift status and compute an overall stability score.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


_PSI_BINS = 10
_PSI_EPS = 1e-4  # Prevents log(0) or division by zero


# ─── PSI helpers ─────────────────────────────────────────────────────────────

def _psi_numeric(ref: np.ndarray, cur: np.ndarray, n_bins: int = _PSI_BINS) -> float:
    """Compute PSI for a numeric column using reference-based quantile bins."""
    ref = ref[~np.isnan(ref)]
    cur = cur[~np.isnan(cur)]
    if len(ref) == 0 or len(cur) == 0:
        return 0.0

    # Build bin edges from reference distribution
    quantiles = np.linspace(0, 100, n_bins + 1)
    bin_edges = np.unique(np.percentile(ref, quantiles))
    if len(bin_edges) < 2:
        return 0.0

    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf

    ref_counts, _ = np.histogram(ref, bins=bin_edges)
    cur_counts, _ = np.histogram(cur, bins=bin_edges)

    ref_pct = ref_counts / len(ref)
    cur_pct = cur_counts / len(cur)

    # Clip to epsilon to avoid log(0)
    ref_pct = np.clip(ref_pct, _PSI_EPS, None)
    cur_pct = np.clip(cur_pct, _PSI_EPS, None)

    psi = float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))
    return round(psi, 6)


def _psi_categorical(ref: pd.Series, cur: pd.Series) -> float:
    """Compute PSI for a categorical column using reference categories as bins."""
    ref_counts = ref.value_counts(normalize=True)
    cur_counts = cur.value_counts(normalize=True)

    # Align on all categories in reference; unknown categories in current → small bucket
    all_cats = ref_counts.index.union(cur_counts.index)
    ref_pct = ref_counts.reindex(all_cats, fill_value=_PSI_EPS)
    cur_pct = cur_counts.reindex(all_cats, fill_value=_PSI_EPS)

    psi = float(np.sum((cur_pct.values - ref_pct.values) * np.log(cur_pct.values / ref_pct.values)))
    return round(psi, 6)


# ─── KS test ─────────────────────────────────────────────────────────────────

def _ks_test(ref: np.ndarray, cur: np.ndarray) -> tuple[float, float]:
    """Return (statistic, p_value) from a two-sample KS test."""
    ref = ref[~np.isnan(ref)]
    cur = cur[~np.isnan(cur)]
    if len(ref) < 2 or len(cur) < 2:
        return 0.0, 1.0
    result = stats.ks_2samp(ref, cur)
    return round(float(result.statistic), 6), round(float(result.pvalue), 6)


# ─── PSI severity ────────────────────────────────────────────────────────────

def _psi_severity(psi: float) -> str:
    if psi < 0.10:
        return "stable"
    if psi < 0.20:
        return "moderate"
    return "critical"


# ─── Overall score & verdict ─────────────────────────────────────────────────

def _drift_score(feature_results: list[dict]) -> int:
    """
    0-100 health score. Starts at 100 and penalises based on drifted features.
    Critical drift: −20 per feature; moderate drift: −10; KS-only drift: −5.
    """
    if not feature_results:
        return 100
    penalty = 0
    for f in feature_results:
        sev = f.get("psi_severity", "stable")
        ks_drift = f.get("ks_drift", False)
        if sev == "critical":
            penalty += 20
        elif sev == "moderate":
            penalty += 10
        elif ks_drift:
            penalty += 5

    # Normalise penalty relative to number of features, cap at 100
    normalised = (penalty / len(feature_results)) * (len(feature_results) ** 0.5)
    score = max(0, round(100 - normalised))
    return score


def _verdict(score: int) -> str:
    if score >= 80:
        return "Stable"
    if score >= 50:
        return "Moderate drift"
    return "Significant drift"


# ─── Serialisation helper ─────────────────────────────────────────────────────

def _py(val):
    if val is None or (isinstance(val, float) and val != val):
        return None
    if hasattr(val, "item"):
        return val.item()
    return val


# ─── Distribution snapshots for charts ───────────────────────────────────────

def _numeric_histogram(series: pd.Series, n_bins: int = 20) -> dict:
    """Return {labels, ref_counts} for a histogram chart."""
    arr = series.dropna().values.astype(float)
    if len(arr) == 0:
        return {"labels": [], "counts": []}
    counts, edges = np.histogram(arr, bins=n_bins)
    labels = [round(float((edges[i] + edges[i + 1]) / 2), 4) for i in range(len(edges) - 1)]
    return {"labels": labels, "counts": counts.tolist()}


def _categorical_frequencies(series: pd.Series, top_n: int = 15) -> dict:
    """Return {labels, counts} for top categories."""
    vc = series.value_counts().head(top_n)
    return {"labels": vc.index.astype(str).tolist(), "counts": vc.tolist()}


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def analyse(
    ref_df: pd.DataFrame,
    cur_df: pd.DataFrame,
    n_bins: int = 10,
) -> dict:
    """
    Compare *cur_df* against *ref_df* for dataset drift.

    Parameters
    ----------
    ref_df  : Reference (baseline) DataFrame.
    cur_df  : Current (production/new) DataFrame.
    n_bins  : Number of bins for numeric PSI calculation.

    Returns
    -------
    Structured dict with summary, per-feature drift results, and chart data.
    """
    if len(ref_df) < 10:
        raise ValueError("Reference dataset must have at least 10 rows.")
    if len(cur_df) < 10:
        raise ValueError("Current dataset must have at least 10 rows.")

    # ── Align common columns ─────────────────────────────────────────────────
    common_cols = [c for c in ref_df.columns if c in cur_df.columns]
    if not common_cols:
        raise ValueError("No common columns found between the two datasets.")

    ref_df = ref_df[common_cols].copy()
    cur_df = cur_df[common_cols].copy()

    numeric_cols = ref_df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = [c for c in common_cols if c not in numeric_cols]

    # ── Per-feature analysis ─────────────────────────────────────────────────
    feature_results: list[dict] = []
    chart_data: dict[str, dict] = {}

    # Numeric features
    for col in numeric_cols:
        ref_arr = ref_df[col].values.astype(float)
        cur_arr = cur_df[col].values.astype(float)

        psi = _psi_numeric(ref_arr, cur_arr, n_bins=n_bins)
        ks_stat, ks_pval = _ks_test(ref_arr, cur_arr)
        sev = _psi_severity(psi)
        ks_drift = ks_pval < 0.05

        # Reference stats
        ref_clean = ref_arr[~np.isnan(ref_arr)]
        cur_clean = cur_arr[~np.isnan(cur_arr)]

        feature_results.append({
            "feature": col,
            "type": "numeric",
            "psi": psi,
            "psi_severity": sev,
            "ks_statistic": ks_stat,
            "ks_p_value": ks_pval,
            "ks_drift": ks_drift,
            "drift_detected": sev != "stable" or ks_drift,
            "ref_mean": round(float(np.nanmean(ref_arr)), 4) if len(ref_clean) else None,
            "cur_mean": round(float(np.nanmean(cur_arr)), 4) if len(cur_clean) else None,
            "ref_std": round(float(np.nanstd(ref_arr)), 4) if len(ref_clean) else None,
            "cur_std": round(float(np.nanstd(cur_arr)), 4) if len(cur_clean) else None,
            "ref_median": round(float(np.nanmedian(ref_arr)), 4) if len(ref_clean) else None,
            "cur_median": round(float(np.nanmedian(cur_arr)), 4) if len(cur_clean) else None,
            "ref_nulls_pct": round(float(np.isnan(ref_arr).mean() * 100), 2),
            "cur_nulls_pct": round(float(np.isnan(cur_arr).mean() * 100), 2),
        })

        chart_data[col] = {
            "type": "numeric",
            "ref": _numeric_histogram(ref_df[col]),
            "cur": _numeric_histogram(cur_df[col]),
        }

    # Categorical features
    for col in categorical_cols:
        ref_series = ref_df[col].astype(str).fillna("__null__")
        cur_series = cur_df[col].astype(str).fillna("__null__")

        psi = _psi_categorical(ref_series, cur_series)
        sev = _psi_severity(psi)

        ref_n_unique = ref_series.nunique()
        cur_n_unique = cur_series.nunique()

        feature_results.append({
            "feature": col,
            "type": "categorical",
            "psi": psi,
            "psi_severity": sev,
            "ks_statistic": None,
            "ks_p_value": None,
            "ks_drift": None,
            "drift_detected": sev != "stable",
            "ref_n_unique": int(ref_n_unique),
            "cur_n_unique": int(cur_n_unique),
            "ref_nulls_pct": round(float((ref_df[col].isna()).mean() * 100), 2),
            "cur_nulls_pct": round(float((cur_df[col].isna()).mean() * 100), 2),
        })

        chart_data[col] = {
            "type": "categorical",
            "ref": _categorical_frequencies(ref_series),
            "cur": _categorical_frequencies(cur_series),
        }

    # ── Sort: most drifted first ─────────────────────────────────────────────
    _sev_order = {"critical": 0, "moderate": 1, "stable": 2}
    feature_results.sort(key=lambda f: (_sev_order.get(f["psi_severity"], 2), -f["psi"]))

    # ── Overall metrics ───────────────────────────────────────────────────────
    drifted = [f for f in feature_results if f["drift_detected"]]
    critical = [f for f in feature_results if f["psi_severity"] == "critical"]
    moderate = [f for f in feature_results if f["psi_severity"] == "moderate"]
    stable = [f for f in feature_results if f["psi_severity"] == "stable"]

    score = _drift_score(feature_results)

    # Numeric-only KS summary
    numeric_results = [f for f in feature_results if f["type"] == "numeric"]
    ks_drifted = [f for f in numeric_results if f.get("ks_drift")]

    return {
        "summary": {
            "ref_rows": len(ref_df),
            "cur_rows": len(cur_df),
            "total_features": len(common_cols),
            "numeric_features": len(numeric_cols),
            "categorical_features": len(categorical_cols),
            "drifted_count": len(drifted),
            "drifted_pct": round(len(drifted) / len(common_cols) * 100, 1) if common_cols else 0.0,
            "critical_count": len(critical),
            "moderate_count": len(moderate),
            "stable_count": len(stable),
            "ks_drifted_count": len(ks_drifted),
            "score": score,
            "verdict": _verdict(score),
            "n_bins": n_bins,
        },
        "features": feature_results,
        "chart_data": chart_data,
    }
