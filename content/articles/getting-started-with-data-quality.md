---
title: "Getting Started with Data Quality for ML"
slug: getting-started-with-data-quality
date: "2025-01-15"
description: "Why data quality matters more than model choice, and how to audit your dataset before training."
tags:
  - data quality
  - machine learning
  - best practices
  - data preparation
---

## Why data quality beats model selection

Every ML practitioner eventually learns the hard way: you can spend weeks tuning a model, swapping architectures, and adjusting hyperparameters — but if the training data is messy, performance will plateau. The phrase "garbage in, garbage out" has been around since the 1960s for good reason.

Research consistently shows that data quality improvements yield larger performance gains than model complexity increases. A cleaned, well-structured dataset with a simple logistic regression will often outperform a state-of-the-art transformer trained on noisy data.

## The four main data quality problems

### 1. Missing values

Missing values are the most common data quality issue. They occur when sensors fail, forms go uncompleted, or joins introduce gaps. The danger isn't just the missing entries themselves — it's the silent bias they introduce.

If customers who churn never complete the "satisfaction score" field, and you drop those rows, your model will be trained on a fundamentally different population than it encounters in production.

**What to check:**
- Missing percentage per column (flag anything above 5%)
- Whether missingness is random or systematic (MCAR vs MAR vs MNAR)
- Correlation between missing columns

### 2. Outliers

Outliers can be legitimate extreme values (a very high-net-worth customer) or data errors (a human age of 999). The problem is distinguishing between them at scale.

IQR-based outlier detection (flagging values outside 1.5× the interquartile range) is a good starting point. For multidimensional data, Isolation Forest or DBSCAN can catch multivariate outliers that look normal column-by-column.

### 3. Duplicate rows

Duplicate rows in training data cause a subtle but serious problem: data leakage. If duplicates appear in both training and validation sets, your model learns to memorise specific examples rather than generalise — inflating validation metrics while failing in production.

Always deduplicate before splitting into train/validation/test sets.

### 4. Mixed data types

A column that should be numeric but contains values like `"N/A"`, `"unknown"`, or `"—"` will be parsed as an object column by pandas. Models that expect numeric features will either crash or silently convert these to NaN. Mixed-type columns require explicit cleaning before encoding.

## A practical audit checklist

Before any model training run, check:

1. **Shape** — How many rows and columns? Is this enough data for your ML stage?
2. **Missing values** — What percentage per column? Which columns are correlated in missingness?
3. **Duplicates** — Are there exact duplicate rows? Fuzzy duplicates?
4. **Type consistency** — Are numeric columns actually numeric? Do categoricals have unexpected values?
5. **Outliers** — Which numeric columns have extreme values? Are they errors or real signals?
6. **Class balance** — For classification tasks, what is the ratio between classes?

---

## Try the xariff Quality Checker

Instead of writing all this analysis from scratch, you can upload your CSV to [xariff's Data Quality Checker](/tools/quality) and get:

- A **0–100 quality score** with column-level breakdown
- **Missing value percentages** per column
- **Outlier counts** using IQR detection
- **Mixed type detection**
- **Downloadable flagged rows** as CSV
- Actionable verdict: Healthy / Needs attention / Critical

It takes about 10 seconds and requires no signup.

For a full ML readiness evaluation — including class balance, data volume checks, and a shareable report — try the [ML Readiness Scorecard](/tools/scorecard).

---

## Summary

Data quality is not glamorous, but it is foundational. Before tuning your next model:

1. Run a quality check on your dataset
2. Fix missing values systematically (don't just drop rows blindly)
3. Deduplicate before splitting
4. Verify type consistency across all columns
5. Check class balance if you're doing classification

Your future model accuracy will thank you.
