# Project Structure

This document describes the current structure of the `setara3` project.

## Root Overview

```text
setara3/
├── app/                    # FastAPI application code
├── content/                # Markdown content (blog articles)
├── guide/                  # Internal docs, specs, and notes
├── static/                 # Frontend static assets (CSS/JS)
├── templates/              # Jinja2 HTML templates
├── tests/                  # Test suite
├── .env.example            # Example environment variables
├── Dockerfile              # Container build file
├── fly.toml                # Fly.io deployment config
├── requirements.txt        # Python dependencies
├── robots.txt              # Robots rules source
└── xariff.db               # Local SQLite database
```

## `app/` (Backend Application)

```text
app/
├── main.py                 # FastAPI app setup, middleware, router registration
├── config.py               # Runtime settings from env vars
├── database.py             # SQLAlchemy async engine/session setup
├── models.py               # SQLAlchemy ORM models
├── dependencies.py         # Shared FastAPI dependencies
├── routers/                # HTTP routes (pages + APIs)
├── services/               # Core analysis and business logic
├── schemas/                # Pydantic models/schemas
└── utils/                  # Reusable helper modules
```

### `app/routers/`
- `pages.py`: main pages (`/`, `/about`, legal pages, `/tools`)
- `tools.py`: tool page routes (quality, scorecard)
- `analysis.py`: quality and scorecard analysis endpoints
- `profiler.py`: profiler page + analysis API
- `coverage.py`: coverage page + analysis API
- `outliers.py`: outlier analysis API
- `drift.py`: drift analysis API
- `articles.py`: blog listing and article pages
- `reports.py`: report page routes
- `api.py`: shared APIs (email capture, feedback, tracking, sitemap/robots, sample data)

### `app/services/`
- `quality.py`, `scorecard.py`: dataset quality scoring logic
- `profiler.py`: dataset profiling logic
- `coverage.py`: feature-space coverage analysis
- `outliers.py`: outlier detection logic
- `drift.py`: data drift analysis logic
- `bias.py`, `labels.py`, `redundancy.py`: placeholder/minimal service modules

### `app/utils/`
- `markdown.py`: markdown/frontmatter loading helpers
- `legal.py`: legal content/policy helpers
- `analytics.py`: analytics event helper logic
- `charts.py`: chart/data formatting helpers

## `templates/` (Server-Rendered Views)

```text
templates/
├── base.html               # Shared layout
├── home.html               # Landing page
├── about.html              # About page
├── report.html             # Generated report view
├── partials/               # Shared UI fragments
├── legal/                  # Terms, privacy, cookies pages
├── blog/                   # Blog index + article template
└── tools/                  # Tool pages + partial result templates
```

## `static/` (Frontend Assets)

```text
static/
├── css/
│   └── custom.css          # Main stylesheet
└── js/
    ├── app.js              # Shared frontend behavior
    ├── profiler.js         # Profiler tool interactions
    ├── coverage.js         # Coverage tool interactions
    ├── outliers.js         # Outliers tool interactions
    └── drift.js            # Drift tool interactions
```

## `content/` (CMS-Like Content Source)

```text
content/
└── articles/               # Blog articles in Markdown
```

## `tests/` (Automated Tests)

```text
tests/
├── test_api.py             # API and endpoint behavior tests
└── test_quality.py         # Quality analysis tests
```

## `guide/` (Project Documentation)

Contains implementation notes, specs, TODOs, and architecture docs for team/internal use.
