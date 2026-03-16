---
title: "Welcome to xariff: Fast ML Dataset Checks in One Place"
slug: welcome-to-xariff-fast-ml-dataset-checks-in-one-place
date: "2026-03-16"
description: "xariff provides six free ML dataset tools — profiler, quality checker, readiness scorecard, coverage analysis, outlier detection, and drift monitoring — all with a single CSV upload."
author: "xariff"
tags:
  - xariff
  - dataset tools
  - machine learning
  - quick start
---

xariff helps you assess the health of an ML dataset before model training or deployment. Upload a CSV file, run a focused check, and get clear results — no setup, no signup, no infrastructure required.

If you work with ML data regularly, the goal is to find data risk early so that model work does not stall on problems that could have been caught in minutes.

## What xariff does

xariff provides six focused tools. Each tool answers a specific question about your dataset. You can run one or all six depending on where you are in the ML workflow.

1. [Dataset Profiler](/tools/profiler) — what does this dataset look like?
2. [Quality Checker](/tools/quality) — how many data quality issues does it have?
3. [ML Readiness Scorecard](/tools/scorecard) — is this dataset ready to train a model?
4. [Feature-Space Coverage](/tools/coverage) — are there sparse regions the model won't learn from?
5. [Outlier Detector](/tools/outliers) — which rows are anomalous?
6. [Drift Detector](/tools/drift) — has the data distribution changed since baseline?

All tools are free. All tools work by uploading a CSV — nothing to install, no API keys, no configuration files.

## Quick guide to each tool

### 1. Dataset Profiler

**Use when**: You have a new or unfamiliar dataset and need a quick overview before deciding what to do next.

Upload a CSV and get: row and column count, missing value rates, duplicate row detection, per-column statistics (mean, median, standard deviation, min, max), distribution histograms, and basic correlation analysis.

The profiler takes roughly 5 seconds on a typical dataset. It is the right starting point for any dataset you have not seen before.

### 2. Quality Checker

**Use when**: You want a direct quality assessment with a score and a prioritised list of issues.

Upload a CSV and get: a 0–100 quality score, missing value analysis per column, duplicate detection, mixed-type warnings, outlier counts, and a downloadable CSV of flagged rows.

The quality score consolidates multiple failure modes into one number. A score below 70 typically means cleanup work will have more impact than modelling choices.

### 3. ML Readiness Scorecard

**Use when**: You need a go/no-go decision on whether a dataset is ready to train a model.

Upload a CSV and get: an overall ML readiness score across five dimensions — quality, completeness, class balance, data volume, and uniqueness — plus dimension-level scores and specific recommendations on what to fix.

The scorecard is designed to be shared. Each analysis produces a permanent report link you can send to collaborators or include in documentation.

### 4. Feature-Space Coverage

**Use when**: You want to understand whether the dataset covers the full range of cases the model will encounter in production.

Upload a CSV and get: a coverage score, a 2D feature-space map highlighting sparse and empty regions, and profiles of underrepresented feature ranges.

Coverage gaps indicate blind spots — areas where the model will have to extrapolate rather than interpolate. The coverage tool makes these visible before training.

### 5. Outlier Detector

**Use when**: Anomalous rows are likely to be present and could affect model stability or evaluation accuracy.

Upload a CSV and get: Isolation Forest and DBSCAN outlier detection, an ensemble anomaly view, per-row anomaly scores, feature-level contribution signals, and an outlier health score.

Three detection methods in one run — more comprehensive than any single algorithm on its own.

### 6. Drift Detector

**Use when**: You have a baseline dataset and a current dataset and want to check whether the distribution has shifted.

Upload two CSVs (reference and current) and get: feature-level drift analysis using PSI and the KS test, drift severity labels (stable / moderate / significant), an overall stability score, and distribution comparison charts.

The drift tool is the standard first check when a deployed model's performance has changed unexpectedly.

## Recommended workflow for a new dataset

This sequence takes 5–10 minutes and covers the most common pre-training risk factors:

1. Run **Dataset Profiler** to understand shape, types, and distributions.
2. Run **Quality Checker** to identify and prioritise data issues.
3. Run **ML Readiness Scorecard** to get a structured readiness decision.
4. Add **Outlier Detector**, **Coverage**, or **Drift** checks based on your specific use case.

## FAQ

### Is xariff free to use?

Yes. All six tools are free. No signup or account is required. Upload a CSV and start immediately.

### What file types does xariff support?

xariff supports CSV and TSV files up to 50MB, 500,000 rows, and 50 columns. Most standard ML tabular datasets fit within these limits.

### Does xariff store uploaded data?

Uploaded files are processed in memory for the duration of the analysis and are not stored. See the [privacy policy](/privacy) for details.

### Which tool should I start with?

Start with the Dataset Profiler if you are exploring a new dataset. Start with the Quality Checker if your focus is data cleaning. Start with the ML Readiness Scorecard if you need a go/no-go training decision. Start with the Drift Detector if you suspect your production data has shifted from your training baseline.

### Can I use xariff for production monitoring?

The Drift Detector is designed for production monitoring use cases — upload your baseline and current data on a regular schedule to track distribution shift across features. The other tools are designed primarily for pre-training dataset assessment.
