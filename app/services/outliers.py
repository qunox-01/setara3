"""
Outlier Detection Service
Implements Isolation Forest, DBSCAN, and an ensemble mode.

Pipeline:
  1. Prepare numeric features (standardize)
  2. Run Isolation Forest  → anomaly scores + labels
  3. Run DBSCAN            → cluster labels (-1 = noise)
  4. Ensemble              → consensus flags
  5. Summarise             → per-row details, feature contributions, score
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


# ─── 1. Feature Preparation ──────────────────────────────────────────────────

def prepare_features(df: pd.DataFrame, label_col: str | None = None):
    """Return scaled numeric matrix, column names, and fitted scaler."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if label_col and label_col in numeric_cols:
        numeric_cols.remove(label_col)
    if len(numeric_cols) < 2:
        raise ValueError(
            f"Need at least 2 numeric columns for outlier detection. Found: {len(numeric_cols)}."
        )
    X = df[numeric_cols].values.astype(float)
    X = np.nan_to_num(X, nan=0.0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    return X_scaled, numeric_cols, scaler


# ─── 2. Isolation Forest ─────────────────────────────────────────────────────

def run_isolation_forest(
    X_scaled: np.ndarray,
    contamination: float = 0.05,
    random_state: int = 42,
) -> dict:
    """
    Fit Isolation Forest and return per-row labels and scores.

    Returns
    -------
    dict with keys:
      labels        : np.ndarray of int  (1 = inlier, -1 = outlier)
      scores        : np.ndarray of float (higher = more anomalous, range 0-1)
      raw_scores    : np.ndarray of float (raw decision function, negative = outlier)
      outlier_mask  : np.ndarray of bool
      outlier_count : int
      contamination : float used
    """
    contamination = float(np.clip(contamination, 0.001, 0.5))
    clf = IsolationForest(contamination=contamination, random_state=random_state, n_jobs=-1)
    labels = clf.fit_predict(X_scaled)            # 1 = inlier, -1 = outlier
    raw_scores = clf.decision_function(X_scaled)  # negative → outlier
    # Normalise to [0, 1] where 1 = most anomalous
    scores = 1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-10)
    outlier_mask = labels == -1
    return {
        "labels": labels,
        "scores": scores,
        "raw_scores": raw_scores,
        "outlier_mask": outlier_mask,
        "outlier_count": int(outlier_mask.sum()),
        "contamination": contamination,
    }


# ─── 3. DBSCAN ───────────────────────────────────────────────────────────────

def _auto_eps(X_scaled: np.ndarray, min_samples: int) -> float:
    """Estimate eps via k-distance plot elbow (95th percentile of k-NN distances)."""
    k = min(min_samples, len(X_scaled) - 1)
    nn = NearestNeighbors(n_neighbors=k, n_jobs=-1)
    nn.fit(X_scaled)
    distances, _ = nn.kneighbors(X_scaled)
    k_distances = np.sort(distances[:, -1])
    # Use the 95th percentile as a robust elbow proxy
    return float(np.percentile(k_distances, 95))


def run_dbscan(
    X_scaled: np.ndarray,
    eps: float | None = None,
    min_samples: int | None = None,
) -> dict:
    """
    Fit DBSCAN and return cluster labels.

    Returns
    -------
    dict with keys:
      labels        : np.ndarray of int  (-1 = noise/outlier)
      outlier_mask  : np.ndarray of bool
      outlier_count : int
      n_clusters    : int
      eps           : float used
      min_samples   : int used
      cluster_sizes : dict {cluster_id: count}
    """
    n = len(X_scaled)
    if min_samples is None:
        min_samples = max(2, min(10, int(np.log(n)) + 1))
    if eps is None:
        eps = _auto_eps(X_scaled, min_samples)

    db = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1)
    labels = db.fit_predict(X_scaled)
    outlier_mask = labels == -1
    unique_labels = set(labels) - {-1}
    cluster_sizes = {int(lbl): int((labels == lbl).sum()) for lbl in sorted(unique_labels)}

    return {
        "labels": labels,
        "outlier_mask": outlier_mask,
        "outlier_count": int(outlier_mask.sum()),
        "n_clusters": len(unique_labels),
        "eps": round(eps, 4),
        "min_samples": min_samples,
        "cluster_sizes": cluster_sizes,
    }


# ─── 4. Feature Contributions ────────────────────────────────────────────────

def compute_feature_contributions(
    df: pd.DataFrame,
    feature_names: list[str],
    outlier_mask: np.ndarray,
) -> list[dict]:
    """
    For each feature, compare outlier vs. inlier distributions to quantify
    how much that feature drives the outlier detection.
    """
    inlier_mask = ~outlier_mask
    contributions = []

    for feat in feature_names:
        col = pd.to_numeric(df[feat], errors="coerce")
        outlier_vals = col[outlier_mask].dropna()
        inlier_vals = col[inlier_mask].dropna()

        if len(outlier_vals) == 0 or len(inlier_vals) == 0:
            continue

        outlier_mean = float(outlier_vals.mean())
        inlier_mean = float(inlier_vals.mean())
        inlier_std = float(inlier_vals.std()) or 1.0
        z_shift = abs(outlier_mean - inlier_mean) / inlier_std

        contributions.append({
            "feature": feat,
            "outlier_mean": round(outlier_mean, 4),
            "inlier_mean": round(inlier_mean, 4),
            "inlier_std": round(inlier_std, 4),
            "mean_shift_z": round(z_shift, 4),
            "outlier_q25": round(float(outlier_vals.quantile(0.25)), 4),
            "outlier_q75": round(float(outlier_vals.quantile(0.75)), 4),
            "inlier_q25": round(float(inlier_vals.quantile(0.25)), 4),
            "inlier_q75": round(float(inlier_vals.quantile(0.75)), 4),
        })

    contributions.sort(key=lambda x: -x["mean_shift_z"])
    return contributions


# ─── Serialisation helper ────────────────────────────────────────────────────

def _py(val):
    """Convert numpy / pandas scalars to native Python types for JSON serialisation."""
    if val is None or (isinstance(val, float) and val != val):  # None or NaN
        return None
    if hasattr(val, "item"):   # numpy scalar (int64, float64, bool_, …)
        return val.item()
    return val


# ─── 5. Score & Verdict ──────────────────────────────────────────────────────

def _outlier_score(outlier_pct: float) -> int:
    """Return a data-health score 0-100 (higher = fewer outliers = healthier)."""
    penalty = min(100.0, outlier_pct * 4)
    return max(0, round(100 - penalty))


def _verdict(score: int) -> str:
    if score >= 80:
        return "Healthy"
    if score >= 50:
        return "Needs attention"
    return "Critical"


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def analyse(
    df: pd.DataFrame,
    method: str = "ensemble",
    contamination: float = 0.05,
    eps: float | None = None,
    min_samples: int | None = None,
    label_col: str | None = None,
) -> dict:
    """
    Run outlier detection on *df*.

    Parameters
    ----------
    df            : input DataFrame
    method        : "isolation_forest" | "dbscan" | "ensemble"
    contamination : fraction of expected outliers (Isolation Forest)
    eps           : DBSCAN neighbourhood radius (auto if None)
    min_samples   : DBSCAN minimum cluster size (auto if None)
    label_col     : optional column to exclude from features and include in output

    Returns
    -------
    Structured dict with summary, per-method results, outlier rows, and
    feature contributions.
    """
    if len(df) < 10:
        raise ValueError("Dataset must have at least 10 rows for outlier detection.")
    if method not in ("isolation_forest", "dbscan", "ensemble"):
        raise ValueError("method must be one of: isolation_forest, dbscan, ensemble.")

    X_scaled, feature_names, scaler = prepare_features(df, label_col)
    n_rows = len(df)

    # ── Run requested method(s) ──────────────────────────────────────────────
    if_result = db_result = None

    run_if = method in ("isolation_forest", "ensemble")
    run_db = method in ("dbscan", "ensemble")

    if run_if:
        if_result = run_isolation_forest(X_scaled, contamination=contamination)
    if run_db:
        db_result = run_dbscan(X_scaled, eps=eps, min_samples=min_samples)

    # ── Determine primary outlier mask ───────────────────────────────────────
    if method == "isolation_forest":
        primary_mask = if_result["outlier_mask"]
    elif method == "dbscan":
        primary_mask = db_result["outlier_mask"]
    else:  # ensemble: union
        primary_mask = if_result["outlier_mask"] | db_result["outlier_mask"]

    consensus_mask = (
        if_result["outlier_mask"] & db_result["outlier_mask"]
        if (run_if and run_db) else primary_mask
    )

    outlier_count = int(primary_mask.sum())
    outlier_pct = round(outlier_count / n_rows * 100, 2) if n_rows else 0.0
    score = _outlier_score(outlier_pct)

    # ── Feature contributions (based on primary mask) ────────────────────────
    feature_contributions = compute_feature_contributions(df, feature_names, primary_mask)

    # ── Build per-row outlier details (top 200) ──────────────────────────────
    outlier_indices = np.where(primary_mask)[0].tolist()
    outlier_rows = []
    for idx in outlier_indices[:200]:
        row_data: dict = {}
        for feat in feature_names:
            val = df[feat].iloc[idx]
            row_data[feat] = None if pd.isna(val) else _py(val)
        if label_col and label_col in df.columns:
            lbl = df[label_col].iloc[idx]
            row_data[label_col] = None if pd.isna(lbl) else _py(lbl)

        entry: dict = {
            "row_index": int(idx),
            "features": row_data,
            "in_consensus": bool(consensus_mask[idx]) if (run_if and run_db) else None,
        }
        if run_if:
            entry["if_score"] = round(float(if_result["scores"][idx]), 4)
            entry["if_outlier"] = bool(if_result["outlier_mask"][idx])
        if run_db:
            entry["dbscan_label"] = int(db_result["labels"][idx])
            entry["dbscan_outlier"] = bool(db_result["outlier_mask"][idx])

        outlier_rows.append(entry)

    # Sort by anomaly score if available
    if run_if:
        outlier_rows.sort(key=lambda r: -r["if_score"])

    # ── Score distribution (all rows, for scatter/histogram) ─────────────────
    score_distribution = []
    sample_n = min(2000, n_rows)
    sampled_idx = (
        np.random.default_rng(42).choice(n_rows, size=sample_n, replace=False)
        if n_rows > sample_n else np.arange(n_rows)
    )
    for idx in sampled_idx.tolist():
        entry = {
            "row_index": int(idx),
            "is_outlier": bool(primary_mask[idx]),
            "in_consensus": bool(consensus_mask[idx]) if (run_if and run_db) else None,
        }
        if run_if:
            entry["if_score"] = round(float(if_result["scores"][idx]), 4)
        if run_db:
            entry["dbscan_label"] = int(db_result["labels"][idx])
        score_distribution.append(entry)

    # ── Build methods block ──────────────────────────────────────────────────
    methods_block: dict = {}
    if run_if:
        methods_block["isolation_forest"] = {
            "outlier_count": int(if_result["outlier_count"]),
            "outlier_pct": round(if_result["outlier_count"] / n_rows * 100, 2),
            "contamination": float(if_result["contamination"]),
            "avg_anomaly_score": round(float(if_result["scores"].mean()), 4),
            "avg_outlier_score": round(float(if_result["scores"][if_result["outlier_mask"]].mean()), 4)
            if if_result["outlier_count"] > 0 else None,
        }
    if run_db:
        methods_block["dbscan"] = {
            "outlier_count": int(db_result["outlier_count"]),
            "outlier_pct": round(db_result["outlier_count"] / n_rows * 100, 2),
            "n_clusters": int(db_result["n_clusters"]),
            "eps": float(db_result["eps"]),
            "min_samples": int(db_result["min_samples"]),
            "cluster_sizes": {int(k): int(v) for k, v in db_result["cluster_sizes"].items()},
        }

    consensus_count = int(consensus_mask.sum()) if (run_if and run_db) else outlier_count

    return {
        "summary": {
            "total_rows": n_rows,
            "total_features": len(feature_names),
            "feature_names": feature_names,
            "method": method,
            "outlier_count": outlier_count,
            "outlier_pct": outlier_pct,
            "consensus_count": consensus_count,
            "consensus_pct": round(consensus_count / n_rows * 100, 2) if n_rows else 0.0,
            "score": score,
            "verdict": _verdict(score),
        },
        "methods": methods_block,
        "feature_contributions": feature_contributions,
        "outlier_rows": outlier_rows,
        "outlier_count": outlier_count,
        "score_distribution": score_distribution,
    }
