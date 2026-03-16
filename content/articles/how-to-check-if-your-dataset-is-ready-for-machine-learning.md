---
title: "How to Check If Your Dataset Is Ready for Machine Learning"
slug: how-to-check-if-your-dataset-is-ready-for-machine-learning
date: "2026-03-16"
description: "A practical readiness workflow covering quality, completeness, class balance, data volume, and uniqueness — with thresholds and a go/no-go decision framework."
author: "xariff"
tags:
  - ml readiness
  - dataset quality
  - machine learning
  - data preparation
---

A dataset is ready for machine learning when it is clean enough, complete enough, balanced enough, large enough, and unique enough for the specific task. Each of those five dimensions requires a separate check. Passing all five does not guarantee a good model, but failing any one of them reliably produces a bad one.

## Why readiness checking prevents wasted training runs

Many ML projects underperform because of data issues, not model choice. Catching a 40% duplicate rate before training takes minutes. Catching it after three days of hyperparameter tuning costs time, confidence, and credibility.

A structured readiness check forces the right questions early: Is there enough data? Is the target balanced? Are key columns complete? Is there variation to learn from? Answering these questions before training, rather than during or after, changes the pace of an ML project.

## The five readiness dimensions

### 1. Quality

Quality covers missing values, duplicate rows, mixed types, outliers, and formatting inconsistencies. A high-quality dataset has low missing rates in important columns, no duplicate contamination, consistent column types, and plausible value ranges throughout.

A quality score below 70 out of 100 typically suggests cleanup work will have more impact than modelling choices.

### 2. Completeness

Completeness measures how much of the intended data is actually present. A column is complete when its missing rate is low enough to support training without heavy imputation. Completeness also covers temporal coverage — a dataset that only spans two months may be complete in terms of row count but incomplete in terms of seasonal variation.

### 3. Class balance (for classification tasks)

A heavily imbalanced target distribution means the model can achieve high accuracy by predicting the majority class constantly. An imbalance ratio above 10:1 between the majority and minority class is a warning sign that requires oversampling, undersampling, or class weighting before reliable training is possible.

### 4. Data volume

Volume affects what models and techniques are practical. As a rough guide:
- simple linear models can work from a few hundred rows
- tree-based models typically need 1,000+ rows for reliable generalisation
- deep learning methods benefit from tens of thousands of rows or more

Raw row count is less important than the number of rows per class for classification, or the density of examples relative to the feature space complexity.

### 5. Uniqueness

Uniqueness measures how much genuine variation exists in the dataset. A dataset with 50,000 rows but only 200 truly distinct combinations of features provides much less learning signal than its size suggests. High uniqueness means the dataset covers a wide range of real-world cases.

## Manual readiness checklist

Work through these steps before committing to feature engineering:

1. Identify the label column for supervised tasks. Check its value distribution.
2. Check missing-value rates in key feature columns. Flag anything above 20%.
3. Count exact duplicate rows. Remove confirmed duplicates before splitting.
4. Check class distribution for classification tasks. Flag ratios above 10:1.
5. Confirm total usable row count after removing duplicates and rows with missing targets.
6. Inspect numeric columns for obvious outliers or impossible values.
7. Confirm column types are consistent across rows.
8. Summarise findings in a single readiness view before proceeding.

Use xariff's [ML Readiness Scorecard](/tools/scorecard) to run all five dimensions as a single structured assessment and get a readiness score with specific recommendations.

## How to use the readiness score as a go/no-go decision

A readiness score of 85+ across all five dimensions usually means the dataset is ready to start training with standard methods. A score between 65–84 means specific issues need targeted fixes — the scorecard recommendations will tell you which ones matter most. Below 65, data collection or cleaning effort is typically the highest-leverage investment.

The score is not a hard threshold. A 72 with one weak dimension (e.g. low volume for a simple task) can still produce a useful model. A 72 with multiple weak dimensions usually cannot.

## FAQ

### What is the difference between data quality and ML readiness?

Data quality is one dimension of ML readiness. Readiness also includes class balance, data volume, completeness, and uniqueness. A dataset can be clean in every quality dimension and still fail ML readiness because it is too small, too imbalanced, or lacks variation across the feature space.

### Can a clean dataset still be unfit for machine learning?

Yes. A dataset can have no missing values, no duplicates, and consistent formatting — and still be unfit for ML because it contains too few examples, the target classes are severely imbalanced, or the features contain no meaningful signal for the prediction task.

### How many rows are enough for machine learning?

There is no universal answer. It depends on task complexity, feature count, target balance, and the model family. Simple linear classifiers can generalise from a few hundred rows. Gradient-boosted trees typically need 1,000–10,000 labelled examples to be reliable. Deep learning often needs 10,000+ rows per class. When in doubt, start with a simple model on the available data and evaluate whether performance is limited by data volume or model capacity.

### Should I check readiness only once?

No. A dataset acceptable for early exploration may still be weak for production. Distribution shifts, new data sources, and changes in the label definition can all degrade readiness over time. Run a readiness check at each significant data change: before initial training, before production deployment, and after any major data pipeline update.

### What should I do if my dataset fails the readiness check?

Prioritise fixes based on which dimension scored lowest and which features are most important. A low volume score may require collecting more data. A low balance score may require resampling strategy changes. A low quality score points to specific columns that need cleaning. Fix the highest-impact issues first and re-check before training.

### Does readiness scoring work for unsupervised learning?

The core dimensions still apply but quality and uniqueness matter most. There is no class balance dimension for clustering tasks, but feature coverage, value distributions, and row count all still affect what unsupervised methods can reliably find.
