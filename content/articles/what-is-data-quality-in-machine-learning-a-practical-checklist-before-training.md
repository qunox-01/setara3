---
title: "What Is Data Quality in Machine Learning? A Practical Checklist Before Training"
slug: what-is-data-quality-in-machine-learning-a-practical-checklist-before-training
date: "2026-03-16"
description: "A practical pre-training checklist for missing values, duplicates, mixed types, outliers, and consistency issues — with clear thresholds and fix priorities."
author: "xariff"
tags:
  - data quality
  - machine learning
  - checklist
  - data preparation
---

Data quality in machine learning means the dataset is reliable, consistent, and complete enough to support learning. Poor quality data produces weak or misleading models regardless of algorithm choice. In practice, quality is measured across five failure modes: missing values, duplicate rows, mixed data types, outliers, and formatting inconsistencies.

## Why data quality matters more than model choice

Teams frequently spend time tuning hyperparameters or switching algorithms when the real problem is data. A random forest trained on a clean dataset routinely outperforms a gradient-boosted model trained on dirty data. Catching issues before training avoids this trap.

The cost of bad data compounds downstream: corrupted features leak into validation splits, inflated duplicate counts make accuracy metrics look better than they are, and models shipped to production fail on clean inputs that never appeared during training.

## The five quality failure modes

### 1. Missing values

Missing values force a model to impute, ignore, or fail entirely. A missing rate above 20% in a key predictive column is a red flag. A missing rate above 50% usually means the column should be dropped or the data collection process reviewed.

What to measure:
- Missing count and percentage per column
- Whether missingness is random, systematic, or concentrated in a time range
- Whether missing values cluster together (row-level completeness)

### 2. Duplicate rows

Exact or near-exact duplicates inflate apparent dataset size and create overly optimistic evaluation results. If duplicates appear in both training and test splits, the model memorises those rows and leakage occurs.

What to measure:
- Exact duplicate row count
- Near-duplicate rate (same key columns, minor variation elsewhere)

### 3. Mixed data types

A column intended to hold numeric values but containing entries like "N/A", "unknown", or "—" becomes an object column. This causes silent parsing errors in most ML pipelines and incorrect feature statistics.

What to measure:
- Column dtype vs expected dtype
- Proportion of non-numeric entries in numeric columns
- Free-text contamination in structured fields

### 4. Outliers

Outliers affect mean-based statistics, scale-sensitive models, and distance metrics. Not all outliers are errors — some represent valid rare cases — but a column with 15% of values more than five standard deviations from the mean warrants investigation.

What to measure:
- Z-score or IQR-based outlier rate per numeric column
- Whether high-outlier columns are target-adjacent (more risk)

### 5. Formatting and consistency

Inconsistent capitalisation ("Yes" vs "yes"), unit mixing (km vs miles), date format variation, and trailing whitespace are common sources of silent failure in string and categorical features.

What to measure:
- Category cardinality vs expected cardinality
- Date parsing success rate
- String value normalisation issues

## Practical pre-training checklist

Work through these steps in order before committing to feature engineering:

1. Check missing-value rates in every column. Flag any column above 20%.
2. Count and inspect duplicate rows. Remove confirmed duplicates before splitting.
3. Confirm dtype consistency for all numeric and categorical columns.
4. Run outlier rates on numeric columns. Investigate columns above 5% outlier rate.
5. Review categorical columns for spelling variants and mixed casing.
6. Verify date and ID columns parse without errors.
7. Summarise all issues and prioritise by impact on target or key features.

Use xariff's [Quality Checker](/tools/quality) to run this as an automated assessment and get a 0–100 quality score with a per-column issue breakdown and downloadable flagged rows.

## What a quality score tells you

A score of 90+ typically means the dataset is clean enough to start feature engineering. A score between 70–89 means visible issues exist but are manageable with targeted fixes. Below 70, data cleaning effort is likely to have more impact than any modelling decision.

## FAQ

### Is data quality the same as data usefulness?

No. A dataset can score highly on quality checks — few missing values, no duplicates, consistent types — and still be weak for prediction if the features are not informative, coverage is sparse, or the target variable has too little variation. Quality is a necessary but not sufficient condition for ML performance.

### Are all outliers bad data?

No. An outlier in a medical dataset might represent a genuinely rare condition that matters for the model. An outlier in an age column containing 200 might be a data entry error. The right response depends on the column, the domain, and whether the value is plausible. Outliers should be investigated, not automatically removed.

### Why do duplicate rows hurt model evaluation?

If duplicate rows end up in both training and test splits, the model has effectively memorised those rows and the test accuracy overestimates real-world performance. Even when duplicates stay only in training, they bias the model toward patterns associated with overrepresented rows.

### Should quality checks happen after modeling?

No. Run quality checks before any feature engineering or model training. Discovering data issues after a long training run wastes time and can lead to incorrect conclusions about model capacity. The earlier issues are caught, the less rework is needed.

### How do I prioritise which quality issues to fix first?

Fix issues in columns that are likely predictive of the target first. A 30% missing rate in an uninformative ID column has less impact than a 5% missing rate in your strongest feature. Use feature importance estimates from an initial rough model to guide cleanup priority.

### What is a good missing-value threshold before imputing vs dropping?

A common rule of thumb: impute columns with less than 20% missing if the pattern is random. Between 20–50%, investigate why the data is missing before imputing. Above 50%, consider dropping the column unless domain knowledge makes the column essential — in which case treat the missingness itself as a feature.
