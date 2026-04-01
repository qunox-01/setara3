# Project Structure

This document describes the current structure of the `setara3` project as it exists in the repository today.

## Root Overview

```text
setara3/
├── app/                         # FastAPI backend, routers, services, models, utilities
├── content/                     # Markdown article content for the research section
├── guide/                       # Internal project documentation
├── static/                      # CSS and browser-side JavaScript
├── templates/                   # Jinja2 page, partial, and PDF templates
├── tests/                       # Pytest test suite
├── .env.example                 # Example environment variables
├── Dockerfile                   # Production container build
├── docker-compose.dev.yml       # Local development container setup
├── docker-compose.prod.yml      # Production-oriented compose setup
├── fly.toml                     # Fly.io deployment config
├── requirements.txt             # Python dependencies
├── robots.txt                   # Static robots file served by the app
└── xariff.db                    # Local SQLite database file
```

## `app/` (Backend Application)

```text
app/
├── main.py                      # App startup, router registration, static mount, session cookie middleware
├── config.py                    # Environment-driven runtime settings
├── database.py                  # Async SQLAlchemy engine/session setup and table bootstrap
├── models.py                    # ORM models for reports, tool results, analytics, consent, and contact data
├── dependencies.py              # Shared request helpers and CSV/TSV validation
├── routers/                     # HTTP routes for pages, tools, APIs, articles, and reports
├── schemas/                     # Pydantic request/response schemas
├── services/                    # Analysis logic for each tool
└── utils/                       # Shared helpers for analytics, legal, markdown, charts, and PDFs
```

### `app/routers/`

- `pages.py`: static/site pages such as `/`, `/about`, `/contact`, legal pages, `/tools`, and `/robots.txt`
- `tools.py`: entry pages for the quality and scorecard tools
- `analysis.py`: quality and scorecard analysis flows, flagged-row CSV download, and PDF downloads
- `profiler.py`: profiler tool page, CSV ingestion, analysis endpoint, and PDF download
- `coverage.py`: coverage tool page, analysis endpoint, and PDF download
- `outliers.py`: outlier detection tool page, analysis endpoint, and PDF download
- `drift.py`: drift tool page, dual-dataset analysis endpoint, and PDF download
- `articles.py`: `/research` article index and article pages, plus legacy `/blog` redirects
- `reports.py`: saved scorecard report viewing, sample report redirect, and PDF export
- `api.py`: email capture, feedback, contact form, event tracking, sample data, sitemap, and related utility endpoints

### `app/services/`

- `quality.py`: dataset quality scoring, column diagnostics, duplicate detection, and flagged row extraction
- `scorecard.py`: ML-readiness scorecard analysis and report payload generation
- `profiler.py`: dataset profiling and summary statistics generation
- `coverage.py`: PCA-based feature-space coverage analysis and sparse-region profiling
- `outliers.py`: Isolation Forest, DBSCAN, and ensemble outlier detection
- `drift.py`: dataset drift detection using PSI and KS tests
- `bias.py`, `labels.py`, `redundancy.py`: placeholder Phase 2 service stubs that currently return "coming soon" payloads

### `app/utils/`

- `analytics.py`: persists analytics events to the database
- `charts.py`: small helper for Chart.js-friendly config data
- `legal.py`: legal acceptance validation and consent logging
- `markdown.py`: frontmatter parsing, markdown rendering, reading time, and FAQ extraction for articles
- `pdf.py`: shared PDF rendering for stored tool results using WeasyPrint and Jinja templates

### `app/models.py`

Defines the persisted SQLAlchemy models used by the app:

- `Email`
- `Feedback`
- `ContactMessage`
- `Report`
- `ToolResult`
- `AnalyticsEvent`
- `ConsentLog`

### `app/schemas/`

- `profiler.py`: Pydantic schema definitions used by the profiler flow

## `templates/` (Server-Rendered Views)

```text
templates/
├── base.html                    # Shared site layout
├── home.html                    # Landing page
├── about.html                   # About page
├── contact.html                 # Contact page
├── report.html                  # Browser view for saved scorecard reports
├── report_pdf.html              # Printable/PDF report layout for saved reports
├── blog/                        # Research index and article templates
├── legal/                       # Terms, privacy, and cookies pages
├── partials/                    # Reusable UI fragments
├── pdf/                         # Tool-specific PDF templates
└── tools/                       # Tool pages, partial results, and placeholders
```

### Template Subdirectories

- `templates/blog/`: `index.html`, `article.html`
- `templates/legal/`: `terms.html`, `privacy.html`, `cookies.html`
- `templates/partials/`: email capture, feedback, loading, and share partials
- `templates/pdf/`: `_base.html` and PDF templates for quality, scorecard, profiler, coverage, outliers, and drift
- `templates/tools/`: `index.html`, tool pages (`quality`, `scorecard`, `profiler`, `coverage`, `outliers`, `drift`), `coming_soon.html`, and partial result fragments

## `static/` (Frontend Assets)

```text
static/
├── css/
│   └── custom.css               # Main site stylesheet
└── js/
    ├── app.js                   # Shared frontend behavior
    ├── profiler.js              # Profiler interactions
    ├── coverage.js              # Coverage interactions
    ├── outliers.js              # Outliers interactions
    └── drift.js                 # Drift interactions
```

There is currently no dedicated browser script for the quality or scorecard tools; those flows are handled primarily through server-rendered HTML responses and form submissions.

## `content/` (Article Content)

```text
content/
└── articles/                    # Markdown source files for the research section
```

Current article topics include:

- data quality and dataset readiness
- dataset profiling and coverage gaps
- outlier detection methods
- production drift detection
- sample report / coming soon content

## `tests/` (Automated Tests)

```text
tests/
├── test_api.py                  # Smoke tests for pages, assets, APIs, redirects, and core flows
├── test_pdf_templates.py        # Jinja/PDF template render tests for tool reports
└── test_quality.py              # Unit tests for the quality analysis service
```

## `guide/` (Project Documentation)

```text
guide/
├── project-features.md          # Feature-oriented project notes
├── project-structure.md         # This file
└── todo.txt                     # Open tasks and notes
```

## Notes

- The app boots from `app/main.py` and creates database tables during FastAPI startup.
- SQLite is the default local database via `xariff.db`, but the database URL is configurable through environment variables.
- The user-facing site mixes marketing pages, research content, interactive data-audit tools, and downloadable PDF outputs in one FastAPI/Jinja application.
