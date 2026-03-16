---
title: "How to Detect Data Drift in Production Using PSI and KS Test"
slug: how-to-detect-data-drift-in-production-using-psi-and-ks-test
date: "2026-03-16"
description: "A practical feature-by-feature drift workflow using Population Stability Index (PSI) and the KS test — with threshold guidance and production monitoring steps."
author: "xariff"
tags:
  - data drift
  - psi
  - ks test
  - ml monitoring
---

Data drift means production data no longer follows the same statistical distribution as the reference or training data. When drift occurs, a model that was accurate during validation begins predicting on patterns it did not truly learn, and performance silently degrades. Detecting drift requires comparing old and new datasets feature by feature using statistical tests — most commonly **Population Stability Index (PSI)** and the **Kolmogorov-Smirnov (KS) test**.

## Why drift monitoring matters

A model's accuracy is validated against historical data. If production data shifts enough, the validated accuracy no longer reflects real-world performance. The model still runs, predictions still appear, but the error rate climbs. Without active drift monitoring, teams only discover this through customer complaints or delayed business metric reviews — often weeks after the problem began.

The earlier drift is caught, the lower the cost of correction. Catching a distribution shift in one feature before it has spread to correlated features is much cheaper than a full model retraining cycle.

## Two core detection methods

### 1. Population Stability Index (PSI)

PSI measures how much the distribution of a single feature has changed between a reference dataset and a current dataset. It bins the reference distribution, measures the proportion of values in each bin, then computes how much those proportions have shifted in the current data.

Standard thresholds:
- **PSI below 0.1**: little or no meaningful drift — distribution is stable
- **PSI 0.1 to 0.2**: moderate drift — worth monitoring closely, may need investigation
- **PSI above 0.2**: significant drift — treat as a model reliability risk, investigate immediately

PSI was designed for credit risk monitoring but is widely used in production ML across industries. It is directional — you can see which bins shifted and by how much — which makes it useful for root-cause analysis.

### 2. Kolmogorov-Smirnov (KS) test

The KS test checks whether two numeric samples come from the same underlying distribution. It computes the maximum absolute difference between the two empirical cumulative distribution functions (ECDFs) and returns a p-value indicating statistical significance.

A low p-value (typically below 0.05) means the two distributions are statistically different. The KS statistic itself indicates the magnitude of difference.

KS is more sensitive than PSI for small but consistent distribution shifts, especially in continuous features. PSI is more interpretable and widely understood by business stakeholders. Using both together gives a more complete picture.

## Practical production drift monitoring workflow

1. Choose a stable reference dataset. Training data or a fixed baseline validation window works well.
2. Collect a recent production sample — typically from the last day, week, or batch cycle depending on data volume.
3. Align column names. Only compare features that appear in both datasets.
4. Run PSI for every numeric feature in the reference dataset.
5. Run KS tests on the same numeric features as a secondary signal.
6. Flag any feature with PSI above 0.1 or a significant KS p-value.
7. Prioritise features flagged by both methods — those are the highest-confidence drift signals.
8. Review whether the drift is expected (seasonality, product change), harmless, or a genuine data quality or pipeline issue.
9. Escalate when multiple important features drift together, particularly features with high predictive importance.

Use xariff's [Drift Detector](/tools/drift) to upload reference and current CSVs and get a feature-level drift summary with PSI and KS results, drift severity labels, and distribution comparison charts.

## Interpreting drift in context

Not every drift alert means the model is broken. Some drift is expected. A model trained on summer data will see seasonal drift in winter. A pricing model will see drift after a market event. The question is whether the drifted features are important to model performance and whether the drift is large enough to push predictions into unreliable territory.

Drift in low-importance features is often ignorable. Drift in the top five most predictive features is almost always worth acting on.

## FAQ

### What is the difference between data drift and concept drift?

Data drift means the input feature distributions have changed — the data looks different from what the model was trained on. Concept drift means the relationship between inputs and the target outcome has changed — even if the input data looks the same, the correct output has shifted. Both can degrade model performance but require different responses. Data drift is detectable with feature-level statistics. Concept drift requires monitoring prediction accuracy or outcome labels.

### Is PSI enough by itself for production drift monitoring?

PSI is a strong and interpretable starting point, but it has limitations. It is sensitive to the number of bins chosen and can miss subtle monotonic shifts that the KS test would catch. For production monitoring, combining PSI with KS and tracking prediction distribution changes gives a more robust signal. A three-signal approach — PSI, KS, and prediction score distribution — is recommended for high-stakes models.

### Does every drift alert mean the model needs retraining?

No. Some drift is expected and harmless. If drift appears in a feature that contributes very little to model predictions, it is likely ignorable. Retraining is warranted when drift appears in important features, when PSI exceeds 0.2 in multiple features simultaneously, or when monitored business metrics start to decline. Investigate before retraining — sometimes the issue is in the data pipeline, not the model.

### How often should production drift be checked?

It depends on data velocity and business risk. High-volume systems processing millions of transactions daily should run drift checks daily or even on every batch. Slower-moving systems with weekly data updates can check weekly. The key principle is: check drift at the same frequency at which your data can meaningfully change. More frequent checks on lower-risk features can be relaxed once a stable baseline is established.

### What reference dataset should I use for drift comparison?

The most common choice is the training dataset or the last stable validation window. Avoid using the full historical dataset as a reference if the underlying population has changed over time — this creates a mixed reference that blurs the drift signal. A fixed rolling window (e.g. the 30 days before model deployment) often works better than a static snapshot for production monitoring.

### Can PSI be applied to categorical features?

Yes. For categorical features, PSI uses the proportion of rows in each category value instead of numeric bins. The same thresholds apply. One consideration: if a new category value appears in production that was not in the reference data, it cannot be mapped to a reference bin — this should be treated as a separate alert for new category emergence.
