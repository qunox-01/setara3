from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class BoxPlotStats(BaseModel):
    q1: float
    median: float
    q3: float
    whisker_low: float
    whisker_high: float
    outlier_count: int


class TopValue(BaseModel):
    value: str
    count: int
    pct: float


class FeatureProfile(BaseModel):
    name: str
    dtype: str
    type: str  # "numeric" | "categorical" | "datetime" | "text"
    missing_count: int
    missing_pct: float
    unique_count: int
    unique_pct: float
    stats: Optional[dict] = None
    histogram: Optional[List[HistogramBin]] = None
    box_plot: Optional[BoxPlotStats] = None
    top_values: Optional[List[TopValue]] = None


class DatasetOverview(BaseModel):
    rows: int
    columns: int
    missing_total: int
    missing_pct: float
    duplicate_rows: int
    duplicate_pct: float
    memory_bytes: int
    sampled: bool
    original_rows: Optional[int] = None


class CorrelationMatrix(BaseModel):
    columns: List[str]
    matrix: List[List[Optional[float]]]


class ProfileResponse(BaseModel):
    dataset: DatasetOverview
    features: List[FeatureProfile]
    correlations: Optional[CorrelationMatrix] = None
