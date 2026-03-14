"""
Feature-Space Coverage Service
Implements the 5-step pipeline: standardize → PCA → grid → flag → back-project
"""

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


# ─── Step 1: Standardize ────────────────────────────────────────────────────

def standardize_features(df: pd.DataFrame, label_col: str = None):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if label_col and label_col in numeric_cols:
        numeric_cols.remove(label_col)
    if len(numeric_cols) < 3:
        raise ValueError(
            f"Need at least 3 numeric columns for coverage analysis. Found: {len(numeric_cols)}."
        )
    X = df[numeric_cols].values
    X = np.nan_to_num(X, nan=0.0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    return X_scaled, numeric_cols, scaler


# ─── Step 2: Project to 2D with PCA ─────────────────────────────────────────

def project_to_2d(X_scaled: np.ndarray):
    pca = PCA(n_components=2)
    X_2d = pca.fit_transform(X_scaled)
    explained_var = pca.explained_variance_ratio_
    total_explained = float(explained_var.sum())
    return X_2d, pca, explained_var, total_explained


# ─── Step 3: Grid Overlay and Density ───────────────────────────────────────

def compute_grid_density(X_2d: np.ndarray, grid_size: int = None):
    N = X_2d.shape[0]
    if grid_size is None:
        grid_size = max(6, min(20, int(np.sqrt(N) / 2)))

    x_min, x_max = X_2d[:, 0].min(), X_2d[:, 0].max()
    y_min, y_max = X_2d[:, 1].min(), X_2d[:, 1].max()
    x_pad = (x_max - x_min) * 0.05
    y_pad = (y_max - y_min) * 0.05
    x_edges = np.linspace(x_min - x_pad, x_max + x_pad, grid_size + 1)
    y_edges = np.linspace(y_min - y_pad, y_max + y_pad, grid_size + 1)

    x_idx = np.clip(np.digitize(X_2d[:, 0], x_edges) - 1, 0, grid_size - 1)
    y_idx = np.clip(np.digitize(X_2d[:, 1], y_edges) - 1, 0, grid_size - 1)

    grid_counts = np.zeros((grid_size, grid_size), dtype=int)
    for i in range(N):
        grid_counts[y_idx[i], x_idx[i]] += 1

    cell_assignments = list(zip(x_idx.tolist(), y_idx.tolist()))
    return grid_counts, x_edges, y_edges, cell_assignments, grid_size


# ─── Step 4: Flag Sparse and Empty Cells ────────────────────────────────────

def flag_sparse_cells(grid_counts: np.ndarray, grid_size: int):
    total_samples = grid_counts.sum()
    expected_per_cell = total_samples / (grid_size * grid_size)
    sparse_threshold = max(1, int(expected_per_cell * 0.2))

    flagged = []
    for row in range(grid_size):
        for col in range(grid_size):
            count = grid_counts[row, col]
            if count > sparse_threshold:
                continue
            neighbors = []
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < grid_size and 0 <= nc < grid_size:
                        neighbors.append(grid_counts[nr, nc])
            occupied_neighbors = sum(1 for n in neighbors if n > 0)
            if occupied_neighbors >= 2:
                gap_type = "empty" if count == 0 else "sparse"
                flagged.append({
                    "row": row,
                    "col": col,
                    "count": int(count),
                    "type": gap_type,
                    "occupied_neighbors": occupied_neighbors,
                    "neighbor_total": int(sum(neighbors)),
                })

    flagged.sort(key=lambda x: (0 if x["type"] == "empty" else 1, -x["neighbor_total"]))
    return flagged, sparse_threshold


# ─── Step 5 Helpers ──────────────────────────────────────────────────────────

def _get_nearest_samples(X_2d: np.ndarray, cx: float, cy: float, k: int = 10, exclude: set = None):
    distances = np.sqrt((X_2d[:, 0] - cx) ** 2 + (X_2d[:, 1] - cy) ** 2)
    indices = np.argsort(distances)
    result = []
    for idx in indices:
        if exclude and int(idx) in exclude:
            continue
        result.append(int(idx))
        if len(result) >= k:
            break
    return result


def _compute_confidence(cell: dict, total_explained_var: float, sample_indices: list,
                        X_scaled: np.ndarray, X_2d: np.ndarray) -> dict:
    proj_score = min(1.0, total_explained_var / 0.6)
    interior_score = cell["occupied_neighbors"] / 8

    if len(sample_indices) >= 5:
        subset = sample_indices[:min(20, len(sample_indices))]
        k = min(5, len(subset))
        nn_2d = NearestNeighbors(n_neighbors=k).fit(X_2d[subset])
        nn_orig = NearestNeighbors(n_neighbors=k).fit(X_scaled[subset])
        _, idx_2d = nn_2d.kneighbors(X_2d[subset])
        _, idx_orig = nn_orig.kneighbors(X_scaled[subset])
        overlaps = [len(set(a) & set(b)) / len(a) for a, b in zip(idx_2d, idx_orig)]
        local_score = float(np.mean(overlaps))
    else:
        local_score = 0.5

    confidence = 0.4 * proj_score + 0.3 * interior_score + 0.3 * local_score
    if confidence >= 0.7:
        level = "high"
    elif confidence >= 0.4:
        level = "medium"
    else:
        level = "low"
    return {"score": round(confidence, 2), "level": level}


# ─── Step 5: Back-Project to Original Feature Space ─────────────────────────

def back_project_flagged_cells(
    flagged: list,
    X_scaled: np.ndarray,
    X_2d: np.ndarray,
    df_original: pd.DataFrame,
    feature_names: list,
    scaler,
    pca,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
    cell_assignments: list,
    label_col: str = None,
    total_explained_var: float = 1.0,
) -> list:
    profiles = []
    dataset_medians = df_original[feature_names].median()

    for cell in flagged:
        row, col = cell["row"], cell["col"]
        cx = float((x_edges[col] + x_edges[col + 1]) / 2)
        cy = float((y_edges[row] + y_edges[row + 1]) / 2)

        if cell["type"] == "sparse":
            in_cell = [i for i, (c, r) in enumerate(cell_assignments) if c == col and r == row]
            nearby = _get_nearest_samples(X_2d, cx, cy, k=10, exclude=set(in_cell))
            sample_indices = list(dict.fromkeys(in_cell + nearby))
        else:
            neighbor_indices = []
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = row + dr, col + dc
                    for i, (c, r) in enumerate(cell_assignments):
                        if c == nc and r == nr:
                            neighbor_indices.append(i)
            sample_indices = neighbor_indices if neighbor_indices else _get_nearest_samples(X_2d, cx, cy, k=10)

        if not sample_indices:
            continue

        orig_vals = df_original[feature_names].iloc[sample_indices]
        feature_summary = {}
        for feat in feature_names:
            vals = orig_vals[feat]
            feat_median = float(vals.median())
            dataset_med = float(dataset_medians[feat])
            feature_summary[feat] = {
                "region_median": round(feat_median, 4),
                "region_q25": round(float(vals.quantile(0.25)), 4),
                "region_q75": round(float(vals.quantile(0.75)), 4),
                "dataset_median": round(dataset_med, 4),
                "deviation_from_center": round(abs(feat_median - dataset_med), 4),
            }

        devs = [(f, v["deviation_from_center"]) for f, v in feature_summary.items()]
        devs.sort(key=lambda x: -x[1])
        top_deviating = [f for f, _ in devs[:3]]

        profile: dict = {
            "cell_row": row,
            "cell_col": col,
            "cell_type": cell["type"],
            "sample_count": cell["count"],
            "profile_source": "in-cell" if cell["type"] == "sparse" else "boundary-neighbors",
            "feature_summary": feature_summary,
            "top_deviating_features": top_deviating,
            "nearest_row_indices": sample_indices[:5],
            "confidence": _compute_confidence(cell, total_explained_var, sample_indices, X_scaled, X_2d),
        }

        if label_col and label_col in df_original.columns:
            label_counts = df_original[label_col].iloc[sample_indices].value_counts()
            profile["label_distribution"] = {str(k): int(v) for k, v in label_counts.items()}

        profiles.append(profile)

    return profiles


# ─── Coverage Score ──────────────────────────────────────────────────────────

def compute_coverage_score(grid_counts: np.ndarray, grid_size: int) -> int:
    interior_mask = np.zeros_like(grid_counts, dtype=bool)
    for r in range(grid_size):
        for c in range(grid_size):
            neighbors = []
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < grid_size and 0 <= nc < grid_size:
                        neighbors.append(grid_counts[nr, nc])
            if sum(1 for n in neighbors if n > 0) >= 2:
                interior_mask[r, c] = True

    interior_total = int(interior_mask.sum())
    if interior_total == 0:
        return 100
    interior_occupied = int((grid_counts[interior_mask] > 0).sum())
    return round((interior_occupied / interior_total) * 100)


# ─── Main Entry Point ────────────────────────────────────────────────────────

def analyse(df: pd.DataFrame, label_col: str = None, grid_size: int = None) -> dict:
    if len(df) < 50:
        raise ValueError("Dataset must have at least 50 rows for coverage analysis.")

    X_scaled, feature_names, scaler = standardize_features(df, label_col)

    if len(feature_names) > 50:
        raise ValueError(f"Dataset has {len(feature_names)} features. Maximum allowed is 50.")

    X_2d, pca, explained_var, total_explained = project_to_2d(X_scaled)
    grid_counts, x_edges, y_edges, cell_assignments, gs = compute_grid_density(X_2d, grid_size)
    flagged, sparse_threshold = flag_sparse_cells(grid_counts, gs)
    profiles = back_project_flagged_cells(
        flagged, X_scaled, X_2d, df, feature_names,
        scaler, pca, x_edges, y_edges, cell_assignments,
        label_col, total_explained,
    )
    coverage_score = compute_coverage_score(grid_counts, gs)

    # Nearest rows data: include actual row values for the up to 5 indices in each profile
    nearest_rows_data: dict[str, list] = {}
    for profile in profiles:
        key = f"{profile['cell_row']}_{profile['cell_col']}"
        indices = profile["nearest_row_indices"]
        rows = df.iloc[indices].where(pd.notnull(df.iloc[indices]), other=None)
        nearest_rows_data[key] = rows.to_dict(orient="records")

    return {
        "coverage_score": coverage_score,
        "grid_size": gs,
        "total_samples": len(df),
        "total_features": len(feature_names),
        "feature_names": feature_names,
        "pca_explained_variance": [round(float(v), 4) for v in explained_var],
        "pca_total_explained": round(total_explained, 4),
        "sparse_threshold": int(sparse_threshold),
        "flagged_regions": profiles,
        "grid_data": {
            "counts": grid_counts.tolist(),
            "x_edges": x_edges.tolist(),
            "y_edges": y_edges.tolist(),
        },
        "sample_2d_coords": X_2d.tolist(),
        "sample_labels": df[label_col].astype(str).tolist() if label_col and label_col in df.columns else None,
        "nearest_rows_data": nearest_rows_data,
    }
