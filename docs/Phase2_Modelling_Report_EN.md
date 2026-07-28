# Video Rebuffering Risk Lab — Phase 2: Modelling and Evaluation

> **Status:** Portfolio V1 complete. This report describes the frozen baseline model
> and its one-time row-level ranking evaluation on the locked test split. It does
> not include test-based threshold tuning.

## 1. Phase 2 question

> Can nine numeric features available at chunk-send time rank observations by the
> risk that playback begins rebuffering within five seconds, including on sessions
> the model has never seen?

V1 does not yet decide when to lower video quality. It first asks whether a useful
risk ranking exists.

## 2. Observation, label and eligibility

One observation is an eligible `video_sent` row.

```text
target_5s = 1
if an official rebuffer event in the same session_id + index
starts strictly after the sent timestamp and within five seconds
```

Only reconstructed `playing` rows are eligible. Startup buffering, current
rebuffering and unknown state are excluded.

```text
Eligible rows:       10,877,668
Positive rows:            2,851
Eligible sessions:         3,457
Positive sessions:           189
```

The target is row-level. One freeze episode may generate several positive sent
rows.

## 3. Why the split uses sessions

Rows within one session share:

- a TCP connection;
- nearby network conditions;
- continuous playback-buffer history;
- potentially several labels from the same upcoming freeze.

A random row split would allow session-specific behaviour to appear in both train
and test. V1 therefore isolates `session_id`.

| Split | Sessions | Rows | Positive sessions | Positive rows |
|---|---:|---:|---:|---:|
| Development | 2,765 | 8,648,637 | 151 | 2,190 |
| Locked test | 692 | 2,229,031 | 38 | 661 |

Session overlap:

```text
0
```

The 80/20 allocation is practical, not universal. Positive sessions were ranked by
their number of positive rows and placed into five coarse strata, while all other
sessions formed a `no_positive` stratum. These strata balance the outer split; they
are not CV folds.

Positive concentration is substantial:

```text
Top one development session:   17.75%
Top five sessions:             44.48%
Top ten sessions:              58.05%
```

The row count therefore greatly exceeds the effective number of independent
positive sources.

## 4. Saved development CV folds

Five session-level folds were stored for future model comparison:

| Fold | Sessions | Positive sessions | Positive rows |
|---:|---:|---:|---:|
| 0 | 553 | 30 | 146 |
| 1 | 553 | 30 | 321 |
| 2 | 553 | 30 | 887 |
| 3 | 553 | 30 | 569 |
| 4 | 553 | 31 | 267 |

Each of the 2,765 development sessions is assigned exactly once. Uneven positive
rows reflect the observed concentration; repeatedly changing `random_state` to
make the folds look more even would itself be a form of split tuning.

V1's model specification was fixed in advance, so these folds were not used to
tune it. They remain available for future out-of-fold calibration, threshold
selection or V2 comparison.

## 5. Rule baseline

The fixed simple rule is:

```python
buffer < 1.0
```

Development performance:

```text
TP: 381
FP: 446
FN: 1,809
TN: 8,646,001
Precision: 46.07%
Recall: 17.40%
False-positive rate: 0.0052%
Alert rate: 0.0096%
```

The rule produces relatively pure alerts but misses most positive rows.

Development-only sensitivity analysis:

| Buffer threshold | Alerts | Precision | Recall | FPR |
|---:|---:|---:|---:|---:|
| 0.5 s | 244 | 61.48% | 6.85% | 0.0011% |
| 1.0 s | 827 | 46.07% | 17.40% | 0.0052% |
| 2.0 s | 3,973 | 22.43% | 40.68% | 0.0356% |
| 3.0 s | 16,318 | 9.78% | 72.88% | 0.1703% |
| 5.0 s | 63,746 | 3.17% | 92.37% | 0.7139% |

This table illustrates the Precision–Recall trade-off. It is not a search for the
best test threshold; the baseline remains fixed at one second.

## 6. V1 features

Nine numeric features are available at the sent timestamp:

```text
buffer
size
ssim_index
cwnd
in_flight
min_rtt
rtt
delivery_rate
cum_rebuf
```

`format` is postponed to avoid categorical encoding in the first model. Future ACK
time is excluded.

Network meanings:

- `rtt`: current smoothed TCP round-trip-time estimate, microseconds;
- `min_rtt`: minimum observed RTT, microseconds;
- `cwnd`: congestion window, packets;
- `in_flight`: packets sent but not yet acknowledged;
- `delivery_rate`: TCP delivery-rate estimate, bytes/second.

These are observational associations, not controllable causal treatments.

## 7. Scaling without test leakage

Feature magnitudes range from roughly one for SSIM to millions for chunk size and
delivery rate. `StandardScaler` is fitted incrementally using development data
only:

```text
standardized value = (value - development mean) / development standard deviation
```

```text
Rows used to fit scaler: 8,648,637
Missing feature values:  0
Infinite feature values: 0
```

Test data calls `transform()` only.

## 8. Incremental logistic regression

```python
SGDClassifier(
    loss="log_loss",
    penalty="l2",
    alpha=0.0001,
    learning_rate="optimal",
    average=True,
    random_state=42,
)
```

This remains logistic regression; stochastic gradient descent changes how the
coefficients are learned, not the model family.

- `partial_fit()` processes one Parquet partition at a time;
- L2 regularization discourages extreme coefficients;
- averaged weights reduce sensitivity to the final batches;
- deterministic shuffling supports reproducibility;
- no class weights or negative downsampling change the natural prevalence.

The persisted artifact stores:

```text
scaler
model
features, including their order
```

## 9. What the coefficients say

| Feature | Standardized coefficient |
|---|---:|
| `cum_rebuf` | +0.479306 |
| `buffer` | -0.404970 |
| `cwnd` | -0.075893 |
| `ssim_index` | -0.067439 |
| `in_flight` | -0.051348 |
| `min_rtt` | -0.032900 |
| `size` | +0.017293 |
| `rtt` | +0.013629 |
| `delivery_rate` | +0.006029 |

Because features are standardized, the buffer coefficient means that a
one-standard-deviation buffer increase reduces the model log-odds by 0.405, holding
the other standardized terms fixed. The corresponding odds multiplier is about
`exp(-0.405) = 0.67`.

It does **not** mean that one extra second reduces freeze probability by 40.5%.

The two clearest associations are:

- more historical cumulative rebuffering corresponds to higher near-term risk;
- more current buffer corresponds to lower near-term risk.

Ordinary ANOVA or naive Wald-test deletion is not used because:

- rows are correlated within sessions;
- millions of rows can make tiny effects statistically significant;
- network variables are correlated;
- V1 uses penalized estimation;
- the goal is prediction on unseen sessions, not causal inference.

## 10. Investigating the delivery-rate sign

The near-zero positive coefficient appears to conflict with the physical intuition
that faster delivery should protect playback.

To investigate without touching test, development delivery rate was divided into
tertiles:

```text
Low:    below 32.57 Mbps
Medium: 32.57–89.75 Mbps
High:   at least 89.75 Mbps
```

Positive rates inside coarse buffer bands:

| Buffer band | Low rate | Medium rate | High rate |
|---|---:|---:|---:|
| `< 1 s` | 47.14% (305/647) | 42.94% (76/177) | 0/3; unsupported |
| `1–2 s` | 18.61% (475/2,553) | 5.81% (34/585) | 1/8; unsupported |
| `2–5 s` | 2.560% | 0.276% | 0.104% |
| `>= 5 s` | 0.00462% | 0.00115% | 0.000104% |

In sufficiently populated cells, higher delivery rate generally corresponds to
lower risk. The 0/3 and 1/8 cells are too small to support conclusions.

The fitted `+0.006` therefore should not be narrated as "faster delivery causes
freezes." More plausible explanations are:

- the coefficient is effectively near zero;
- buffer already summarizes much recent network history;
- delivery rate, chunk size, quality and ABR decisions are correlated;
- a past TCP estimate does not guarantee the next five seconds;
- an additive model does not explicitly represent `size / delivery_rate`.

Mechanism features such as transfer-time estimate, buffer margin, queueing delay
and in-flight/cwnd utilization are deferred to V2.

## 11. Why Average Precision

Test prevalence is:

```text
661 / 2,229,031 = 0.029654%
```

An all-negative classifier would have about 99.97% accuracy while detecting
nothing. Average Precision is therefore the primary ranking metric.

```text
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
```

AP summarizes Precision across the risk ranking as Recall changes. It does not
require a fixed operating threshold, and it is not itself Recall or Precision at
one threshold.

## 12. Locked-test result

The frozen model predicted once on 692 unseen test sessions:

```text
Rows:       2,229,031
Positives:        661
Prevalence: 0.029654%
```

Predicted-probability summary:

```text
mean:      0.041735%
median:    0.018491%
90th:      0.022108%
99th:      0.333365%
99.9th:    1.900884%
maximum:  99.99874%
```

Mean predicted risk is approximately 1.41 times observed prevalence, suggesting
some overall overprediction. Extreme near-one predictions also exist. These are
calibration and error-analysis questions, not ranking conclusions.

| Risk ranking | Average Precision |
|---|---:|
| Random/prevalence | 0.0002965 |
| Buffer only (`-buffer`) | 0.3616017 |
| Logistic V1 | **0.5477129** |

Improvement over buffer only:

```text
absolute AP: +0.1861
relative AP: 1.51x
```

The 1,847x ratio over random is mathematically correct but is inflated by the
extremely small prevalence denominator. The meaningful comparison is the increase
from 0.362 to 0.548.

The defensible result statement is:

> The frozen logistic model generalized to unseen sessions and improved the
> ranking of imminent rebuffering risk over a buffer-only baseline, increasing
> Average Precision from 0.362 to 0.548.

## 13. What was not tuned

No Logistic probability threshold was selected on test.

AP is an evaluation score, not a model setting. A PR curve conceptually visits many
thresholds to summarize ranking quality, but it does not choose a deployment
threshold.

If a future system must decide when to reduce quality, the threshold should be
selected from development out-of-fold predictions using an explicit cost trade-off,
then evaluated on a new untouched date.

AP 0.548 does not mean:

- 54.8% of freeze episodes were detected;
- 54.8% of alerts were true;
- classification accuracy was 54.8%.

## 14. Leakage audit

- Session-level train/test overlap is zero;
- scaler fit uses development only;
- model fit uses development only;
- test uses transform and prediction only;
- future ACK is excluded;
- label timestamps are excluded from features;
- rows already rebuffering are excluded;
- delivery-rate diagnostics use development only;
- V1 was not modified after test AP was observed.

## 15. Limitations

1. One day of data cannot establish cross-date generalization.
2. Only 38 test sessions contain positive rows.
3. Session dependence means effective sample size is much smaller than row count.
4. The 955,982 unknown-state rows are excluded.
5. Stream endings may create right-censored negatives.
6. Sent-time buffer and cumulative-rebuffer values can be stale.
7. V1 has no historical trend features.
8. The additive linear model misses nonlinear thresholds and interactions.
9. Calibration, Brier score and operational threshold remain uncompleted.
10. Evaluation is row-level, not freeze-event-level.
11. ABR, format and network-condition subgroup performance remains unmeasured.

## 16. Phase 2 conclusion

The portfolio V1 establishes that:

- low buffer is a strong near-term risk signal;
- additional sent-time telemetry provides material ranking value on unseen sessions;
- session-safe validation still produces AP 0.548;
- an interpretable incremental linear model is a credible first result.

Future research should prioritize:

1. a new untouched date;
2. event-level detection;
3. development out-of-fold calibration and threshold selection;
4. a small, mechanism-driven V2 feature set;
5. only then, nonlinear model comparison.

## References

- [Puffer Data Description](https://puffer.stanford.edu/data-description/)
- [Puffer repository](https://github.com/StanfordSNR/puffer)
- [Puffer paper](https://puffer.stanford.edu/static/puffer/documents/puffer-paper.pdf)
- [scikit-learn: common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html)
- [scikit-learn: cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- [scikit-learn: Precision–Recall curve](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_curve.html)
- [scikit-learn: model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [Davis & Goadrich, The Relationship Between Precision-Recall and ROC Curves](https://doi.org/10.1145/1143844.1143874)

