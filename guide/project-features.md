# Project Features and Routes

This guide lists the current web-app features and the routes that expose them.

## 1) Core Website Pages

- Home page
  - `GET /`
- About page
  - `GET /about`
- Legal pages
  - `GET /terms`
  - `GET /privacy`
  - `GET /cookies`
- Tools landing page
  - `GET /tools`
- Blog
  - `GET /blog` (article listing)
  - `GET /blog/{slug}` (article detail)
- Report page
  - `GET /report/{report_id}`

## 2) Data Quality Tool

Service: `app/services/quality.py`

Features:
- Dataset quality score and verdict
- Missing value and duplicate analysis
- Mixed type detection (object columns)
- IQR outlier count per numeric column
- Flagged row extraction

Routes:
- `GET /tools/quality` (tool page)
- `POST /tools/quality/analyse` (render quality result partial)
- `POST /tools/quality/download` (download flagged rows as CSV)

## 3) ML Readiness Scorecard Tool

Service: `app/services/scorecard.py` (uses `quality.py`)

Features:
- Overall readiness score and verdict
- Dimension checks:
  - Data Quality
  - Completeness
  - Class Balance (optional label column)
  - Data Volume (stage-based thresholds)
  - Uniqueness
- Prioritized recommendations
- Shareable report generation

Routes:
- `GET /tools/scorecard` (tool page)
- `POST /tools/scorecard/analyse` (render scorecard result partial)
- `POST /tools/scorecard/report` (persist report and return shareable link)

## 4) Dataset Profiler Tool

Service: `app/services/profiler.py`

Features:
- Dataset-level summary (rows, columns, missing, duplicates, memory)
- Per-feature profiling by inferred type (numeric/categorical/datetime/text)
- Numeric stats (mean/median/std/variance, quantiles, skewness, kurtosis)
- Histogram and boxplot data for numeric columns
- Top values for categorical/text columns
- Correlation matrix (for 2–30 numeric columns)
- Sampling behavior for very large datasets

Routes:
- `GET /tools/profiler` (tool page)
- `POST /api/tools/profiler/analyze` (JSON response)

## 5) Feature-Space Coverage Tool

Service: `app/services/coverage.py`

Features:
- Standardize numeric features
- PCA projection to 2D
- Grid density analysis
- Sparse/empty region detection
- Back-projected region profiles in original feature space
- Coverage score and confidence levels
- Optional label distribution by flagged region

Routes:
- `GET /tools/coverage` (tool page)
- `POST /api/tools/coverage/analyze` (JSON response)

## 6) Outlier Detection Tool

Service: `app/services/outliers.py`

Features:
- Isolation Forest detection
- DBSCAN detection
- Ensemble mode (union + consensus tracking)
- Outlier percentage, score, and verdict
- Per-row outlier details
- Feature contribution ranking (inlier vs outlier shift)
- Distribution payload for visualization

Routes:
- `POST /api/tools/outliers/analyze` (JSON response)

## 7) Dataset Drift Detection Tool

Service: `app/services/drift.py`

Features:
- Reference vs current dataset comparison
- Numeric drift checks: PSI + KS test
- Categorical drift checks: PSI
- Per-feature drift severity (`stable`, `moderate`, `critical`)
- Overall drift score and verdict
- Chart payloads for numeric/categorical distributions

Routes:
- `POST /api/tools/drift/analyze` (JSON response)

## 8) Shared API Features

From `app/routers/api.py`:

- Email capture
  - `POST /api/email-capture`
- Feedback submission
  - `POST /api/feedback`
- Event tracking
  - `POST /api/track`
- Sample datasets by tool
  - `GET /sample-data/{tool}`
- SEO and crawler endpoints
  - `GET /sitemap.xml`
  - `GET /robots.txt`

## 9) Planned / Coming Soon Services

These service modules exist but currently return `coming_soon` payloads:

- `app/services/bias.py`
- `app/services/labels.py`
- `app/services/redundancy.py`
