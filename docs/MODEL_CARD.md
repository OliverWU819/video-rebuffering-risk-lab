# MODEL_CARD.md

## Model Name

Video Rebuffering Risk Logistic V1

## Model Status

Frozen baseline model. Final row-level ranking evaluation has been performed once
on the locked test split.

## Intended Use

Research prototype for ranking eligible video-chunk send moments by the risk that
the same stream begins rebuffering within the next five seconds.

Potential future use: inform a simulated protective ABR action after a threshold is
selected on development validation data.

## Out-of-Scope Use

- Production TikTok policy;
- automatic bitrate reduction using the current artifact;
- causal claims about network variables;
- startup-delay prediction;
- prediction while the player is already rebuffering;
- users, dates or systems not represented by Puffer without external validation.

## Training Data

Stanford Puffer telemetry from 2026-07-19T11 to 2026-07-20T11 UTC.

```text
Development sessions：2,765
Development rows：8,648,637
Positive sessions：151
Positive rows：2,190
```

Only rows with reconstructed state `playing` are included.

## Target Definition

```text
target_5s = 1
if the next event == "rebuffer" in the same session_id + index occurs
strictly after sent_time and no more than five seconds later
```

The target is row-level. Multiple rows can correspond to one freeze episode.

## Prediction Horizon

Five seconds.

## Features

In fixed order:

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

All are recorded or last known at `sent_time`. No future ACK variables are used.

## Preprocessing

`StandardScaler` fitted only on the 8,648,637 development rows. Test data uses
`transform()` only.

## Estimator

```python
SGDClassifier(
    loss="log_loss",
    penalty="l2",
    alpha=0.0001,
    learning_rate="optimal",
    average=True,
    random_state=42
)
```

Trained incrementally with `partial_fit()` over partitioned Parquet data. No class
weights and no negative downsampling.

## Validation Design

Outer session-level 80/20 split:

```text
Train/development：2,765 sessions
Test：               692 sessions
Overlap：              0 sessions
```

The split stratifies no-positive sessions and five coarse positive-volume strata.
The five separately stored CV folds are within development and were not used to
tune V1.

## Baselines

- Random/prevalence risk ranking;
- continuous buffer-only ranking using `-buffer`;
- fixed development rule `buffer < 1 second`.

## Primary Metric

Average Precision (AP), used as the Precision–Recall ranking summary because the
test prevalence is only 0.029654%.

AP is not Recall, Precision at a chosen threshold, accuracy or event-level
detection rate.

## Test Performance

```text
Test sessions：692
Test rows：2,229,031
Positive rows：661
Positive prevalence：0.029654%
```

| Risk score | Average Precision |
|---|---:|
| Random/prevalence | 0.0002965 |
| Buffer only | 0.3616017 |
| Logistic V1 | 0.5477129 |

Improvement over buffer only:

```text
+0.1861 absolute AP
1.51x relative AP
```

## Coefficients

Standardized coefficients:

| Feature | Coefficient |
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

Coefficients are conditional associations in a regularized additive model, not
causal effects or standalone feature-importance proofs.

## Calibration

Not fully evaluated.

Observed test summary:

```text
Actual prevalence：        0.029654%
Mean predicted probability：0.041735%
Median predicted probability：0.018491%
Maximum predicted probability：99.99874%
```

The mean probability is about 1.41 times the observed prevalence and extreme
predictions exist. A calibration curve, Brier score and error analysis remain
future work.

## Threshold Selection

No Logistic V1 probability threshold has been selected.

The test set was not searched for the best Precision/Recall threshold. AP is the
frozen model's ranking score, not a tuned parameter. Any operational threshold must
be selected from development/out-of-fold predictions and evaluated on a new
untouched date or test set.

## Performance by Subgroup

Formal subgroup test performance has not been completed.

Development-only buffer × delivery-rate analysis found that higher delivery rate
generally corresponded to lower positive rate within sufficiently populated buffer
groups. Very small cells such as 0/3 and 1/8 are not treated as reliable evidence.

## Known Failure Modes

- Stale buffer/cumulative-rebuffer measurements;
- rare, extreme feature combinations producing near-one probabilities;
- positive concentration in a few sessions;
- unseen dates, ABR schemes or connection conditions;
- additive linear structure missing interactions and nonlinear thresholds;
- low-buffer states with too little rate-group support;
- predictions near stream endings where future labels may be censored.

## Data Leakage Checks

- Future ACK excluded;
- `freeze_start_time` and `seconds_until_freeze` excluded from features;
- state must be `playing` at prediction;
- scaler fitted on development only;
- model fitted on development only;
- session overlap is zero;
- delivery-rate diagnostic used development only;
- no test-based model or threshold tuning after AP evaluation.

## Limitations

- One day of Puffer data;
- only 38 positive test sessions;
- row-level rather than freeze-event-level evaluation;
- no clustered uncertainty interval for AP;
- no calibration conclusion;
- no operational threshold;
- no historical rolling features;
- no ABR/format subgroup analysis.

## Operational Interpretation

V1 supports a relative risk ranking:

> Higher score means the sent row should be considered more at risk relative to
> other eligible rows.

It does not yet support:

> Automatically lower quality when probability exceeds X.

That action requires a validation-selected threshold and an explicit cost trade-off
between missed freezes and unnecessary quality reduction.

## Reproducibility

Artifact:

```text
data/processed/logistic_model_v1.joblib
```

Stored dictionary keys:

```text
scaler
model
features
```

After a kernel restart:

```python
artifact = joblib.load(model_path)
scaler = artifact["scaler"]
model = artifact["model"]
feature_columns = artifact["features"]
```

