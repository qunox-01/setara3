# SEO and AEO Optimization Guide

This document is a step-by-step SEO and AEO optimization plan for the current `setara3` app.

It is written for the app as it exists today:

- FastAPI + Jinja server-rendered pages
- public marketing pages
- public tool routes under `/tools/*`
- research articles under `/research/*`
- generated reports and PDFs

The goal is to improve:

- search engine indexing and rankings
- answer engine visibility in ChatGPT, Perplexity, Claude, and similar systems
- crawl hygiene for public vs generated/private pages
- content quality for both classic SEO and answer extraction

## 1. Define What Should and Should Not Be Indexed

Start by classifying every route into one of two groups.

### 1.1 Indexable pages

These are pages that should be discoverable in search and answer engines:

- `/`
- `/about`
- `/contact`
- `/booking`
- `/tools`
- `/tools/quality`
- `/tools/scorecard`
- `/tools/profiler`
- `/tools/coverage`
- `/tools/outliers`
- `/tools/drift`
- `/research`
- `/research/{slug}`
- legal pages if you want them searchable:
  - `/terms`
  - `/privacy`
  - `/cookies`

### 1.2 Non-indexable pages

These pages should generally not be indexed:

- `/api/*`
- `/sample-data/*`
- `/report/{report_id}`
- `/report/{report_id}/pdf`
- `/tools/*/pdf/{result_id}`
- any download-only endpoint
- any generated result page or one-off share page unless intentionally public

### 1.3 Output of this step

Create an internal route inventory with three columns:

- route
- index or noindex
- sitemap yes or no

Do this before any implementation work. Without this, the sitemap and robots rules will drift again.

## 2. Fix Crawl Controls First

Do crawl hygiene before trying to grow traffic.

### 2.1 Update `robots.txt`

Make sure `robots.txt` clearly:

- allows public pages that should rank
- blocks API and generated-result endpoints
- blocks report and PDF result URLs if they are private or thin

Recommended review items:

- keep `/research/` and `/tools/` crawlable
- keep `/api/` disallowed
- keep `/sample-data/` disallowed
- add explicit rules to disallowed  `/report/`
- consider adding explicit rules for `/tools/*/pdf/`

### 2.2 Decide whether to use `noindex` as well

`robots.txt` only controls crawling. It does not always solve indexing problems cleanly for already known URLs.

For pages that may still be accessed publicly but should not appear in search:

- serve a `noindex` meta tag or header
- use this for generated reports if they are public URLs but not intended for organic discovery

### 2.3 Keep AI crawler rules intentional

The app already has AI-crawler-specific rules. Review them and decide:

- which content you want answer engines to cite
- which content you do not want training or crawling access to

Do not allow broad crawling for pages that are generated per user or thin-value pages.

## 3. Repair the Sitemap

The sitemap must reflect the pages you actually want indexed.

### 3.1 Include only canonical public pages

The sitemap should contain:

- core site pages
- the tools landing page
- each public tool page
- the research index
- each article page

It should not contain:

- API endpoints
- downloads
- PDFs
- generated report pages
- temporary or parameterized URLs

### 3.2 Make `lastmod` trustworthy

Avoid manually hard-coded dates where possible.

Preferred sources:

- article frontmatter date for article pages
- file modification time or release date for static pages
- deployment date only as a fallback

### 3.3 Review sitemap cadence

Use reasonable values:

- homepage: weekly or monthly
- tools pages: monthly
- research index: weekly
- article pages: monthly unless frequently updated

### 3.4 Add sitemap review to content publishing

Whenever a new article or new public page is added:

- confirm it appears in the sitemap
- confirm non-public endpoints remain excluded

## 4. Fix Canonicals Across the Site

Canonical errors can suppress rankings even if the content is strong.

### 4.1 Give every indexable page its own canonical

Each public page should output its own absolute canonical URL.

This includes:

- `/`
- `/about`
- `/contact`
- `/booking`
- `/tools`
- every `/tools/*` page
- `/research`
- every `/research/{slug}`
- legal pages if kept indexable

### 4.2 Avoid homepage fallback canonicals

Do not let templates silently fall back to the homepage canonical for pages that should stand on their own.

### 4.3 One URL per intent

Pick one preferred URL per page and keep it consistent in:

- canonical tag
- sitemap
- internal links
- Open Graph URL

## 5. Clean Up Metadata

Metadata should be unique, specific, and written for the actual query intent of each page.

### 5.1 Rewrite page titles

Each page title should:

- lead with the main topic or page intent
- include the brand near the end
- avoid vague or repetitive wording

Examples of target patterns:

- `Research and Resources for ML Dataset Analysis | xariff`
- `About xariff | ML Dataset Analysis`
- `Book a Dataset Audit | xariff`

### 5.2 Rewrite meta descriptions

Each page description should:

- describe the page in plain language
- include the core use case
- mention what the visitor gets
- stay concise and non-repetitive

### 5.3 Add full social metadata

Each important page should have:

- `og:title`
- `og:description`
- `og:url`
- `og:image`
- `twitter:card`
- `twitter:title`
- `twitter:description`
- `twitter:image`

### 5.4 Create branded preview images

Create reusable preview images for:

- homepage
- tools index
- each tool page
- research index
- articles

These improve CTR when URLs are shared and give a cleaner brand presence.

## 6. Add Structured Data by Page Type

Structured data is one of the highest-leverage AEO upgrades for this app.

### 6.1 Keep article structured data

The article pages already have a good base:

- `Article`
- `FAQPage`
- breadcrumb semantics

Keep these and validate them.

### 6.2 Remove invalid or unsupported schema

If site search does not actually exist, remove the `SearchAction` schema rather than shipping inaccurate markup.

### 6.3 Add schema to tool pages
Do not change tool pages as part of this guide revision.

If structured data work is needed, limit it to non-tool-page surfaces:

- homepage
- research index
- article pages
- organization-level schema

### 6.4 Add organization-level schema

Add consistent publisher/organization information site-wide:

- organization name
- URL
- logo
- contact page
- sameAs profiles if available

### 6.5 Validate schema externally

Before release, validate:

- article pages
- homepage
- research index

## 7. Build Topic Clusters Around the Tools

The research section is the main content engine for SEO and AEO.

### 7.1 Map each tool to supporting articles

Create clusters like:

- Quality Checker
  - what is data quality in ML
  - how to fix missing values
  - duplicate leakage before training
- Scorecard
  - how to check if a dataset is ready for ML
  - class imbalance thresholds
  - data volume guidance
- Coverage
  - what are coverage gaps
  - sparse regions and model failure
- Outliers
  - Isolation Forest vs DBSCAN
  - anomaly detection for tabular data
- Drift
  - PSI vs KS test
  - production drift monitoring workflow

### 7.2 Improve internal links

Every article should link to:

- the relevant tool
- at least one related article

### 7.3 Add comparison and decision pages

High-value content opportunities:

- `Data Quality Checker vs Dataset Profiler`
- `PSI vs KS Test for Drift Detection`
- `Isolation Forest vs DBSCAN`
- `Data Quality vs ML Readiness`
- `When to use feature-space coverage analysis`

These often perform well in both search and answer engines because they match how users ask questions.

## 8. Write More Query-Shaped Content

AEO improves when content matches the way people actually ask.

### 8.1 Use question headings

Prefer headings such as:

- What is data drift?
- How do you detect outliers in tabular data?
- What is a good ML dataset quality score?
- How do you know if a dataset is ready for machine learning?

### 8.2 Put the direct answer immediately after the heading

For each heading:

- start with a 1 to 3 sentence direct answer
- then add detail below

This helps featured-snippet style extraction and answer engine quoting.

### 8.3 Keep definitions consistent

Use stable definitions for:

- data quality
- ML readiness
- coverage gaps
- outliers
- drift

Do not vary the wording too much between pages unless the distinction matters.

## 9. Improve E-E-A-T and Trust Signals

For this domain, trust and clarity matter.

### 9.1 Strengthen author and publisher clarity

Every article should clearly show:

- author or organization
- publication date
- updated date if applicable

### 9.2 Add methodology transparency

Where relevant, explain:

- which algorithms are used
- why those algorithms were chosen
- what assumptions they make
- when the outputs should not be over-trusted

### 9.3 Add business identity details

Ensure the site has:

- a clear About page
- a real Contact page
- coherent organization description
- consistent naming between metadata and on-page branding

### 9.4 Add proof where possible

Good additions:

- sample report screenshots
- methodology summaries
- worked examples with sample datasets
- before-and-after interpretation examples

## 10. Improve Page Experience and Performance

Performance is not the first issue here, but it still matters.

### 10.1 Review third-party scripts

Audit:

- Tailwind CDN usage
- HTMX CDN
- Chart.js CDN
- analytics load path

Reduce render-blocking behavior where practical.

### 10.2 Improve Core Web Vitals on key pages

Focus first on:

- homepage
- tools index
- research article pages

### 10.3 Optimize image and asset delivery

For any future social preview images or page visuals:

- compress them
- use appropriate dimensions
- define width and height where applicable

## 11. Standardize a Publishing Workflow

SEO and AEO improvements will decay if they are not part of normal publishing.

### 11.1 For every new public page

Check:

- unique title
- unique meta description
- canonical set correctly
- sitemap inclusion decision made
- robots/noindex decision made
- internal links added
- schema added if relevant

### 11.2 For every new article

Check:

- frontmatter includes title, slug, date, description, tags
- target keyword and query intent are clear
- at least one FAQ section if genuinely useful
- links to relevant tools

### 11.3 For every new generated route

Decide immediately:

- crawl allowed or blocked
- index allowed or noindex
- sitemap included or excluded

Do not leave this implicit.

## 12. Suggested Execution Order

Use this order so technical cleanup happens before content scaling.

### Phase 1: Crawl and index hygiene

1. inventory all routes
2. decide indexable vs non-indexable
3. update `robots.txt`
4. update sitemap logic
5. fix canonical tags

### Phase 2: Metadata and schema

1. rewrite titles and descriptions
2. add page-specific social metadata
3. remove invalid search schema
4. add non-tool-page structured data where needed
5. validate all structured data

### Phase 3: Content cluster expansion

1. improve internal links
2. add comparison pages
3. publish more query-driven research articles
4. tie every article to a relevant tool and related article pages

### Phase 4: Performance and trust polish

1. review third-party asset loading
2. improve social preview assets
3. strengthen About and Contact trust signals
4. add examples and methodology proof

## 13. Recommended Success Metrics

Track progress with a small set of metrics instead of too many dashboards.

### Technical metrics

- number of valid indexable URLs in sitemap
- number of non-indexable URLs blocked or noindexed correctly
- number of pages with correct canonical tags
- number of pages with valid schema

### SEO metrics

- impressions and clicks for tool pages
- impressions and clicks for article pages
- CTR by page type
- indexed page count
- rankings for target non-brand queries

### AEO metrics

- citations or mentions in answer engines
- branded query growth
- referral traffic from answer/search assistants if measurable
- growth in impressions on question-based content

### Product-adjacent metrics

- visits from research articles to tool pages
- tool-page conversion to upload or booking
- bookings or report generation from organic traffic

## 14. Immediate High-Value Tasks

If you only do a short first pass, do these first:

1. fix canonical tags for all public pages
2. update `robots.txt` to block generated report and PDF result URLs
3. tighten the sitemap to include only intended public pages
4. remove the unsupported `SearchAction` schema if search is not real
5. strengthen organization, homepage, and article structured data
6. strengthen internal links between `/research/*` and `/tools/*`

## 15. Final Principle

For this app, the strongest SEO and AEO strategy is not keyword stuffing.

It is:

- technically clean public URLs
- strong crawl discipline
- research articles that answer real ML data questions
- direct, extractable answers written in plain language
- tight internal linking between education and product pages

If the site becomes the clearest source for practical answers about dataset quality, readiness, drift, outliers, and coverage, both SEO and AEO should improve together.
