# DECISION_LOG.md

## D-001: Focus V1 on near-term rebuffering risk

**Date:** 2026-07-23  
**Status:** Accepted  
**Stage:** Project selection

### Context

The original project mixed QoE, CDN allocation, cost optimisation, demand
forecasting and LLM diagnosis. That scope made it difficult to complete one
auditable research loop.

### Decision

V1 predicts near-term playback rebuffering risk from public streaming telemetry.

### Reason

It permits one complete chain from domain definition and leakage audit to baseline,
interpretable model and unseen-session evaluation.

---

## D-002: Use `event == "rebuffer"` as freeze start

**Date:** 2026-07-26  
**Status:** Accepted; reverses early `cum_rebuf` approach  
**Stage:** Target definition

### Context

The first attempt labelled positive `cum_rebuf` increments as freeze starts.

### Evidence

A manual ±2-second timeline showed:

```text
rebuffer：buffer nearly exhausted, cumulative value unchanged
play/resume：buffer recovered, cumulative value increases
```

Puffer documentation defines `rebuffer` as the point at which the client
rebuffers and `play` as resume.

### Decision

```python
freeze_start = client_buffer["event"] == "rebuffer"
```

### Outcome

```text
5,935 freeze starts
671 affected streams
0 duplicate freeze keys
```

The old 5,541-episode results are deprecated.

---

## D-003: Predict only while playback state is `playing`

**Date:** 2026-07-26  
**Status:** Accepted  
**Stage:** Eligibility

### Decision

Map state events as:

```text
init → startup_buffering
startup → playing
rebuffer → rebuffering
play → playing
```

Only `playing` sent rows are eligible.

### Alternatives Rejected

- Include startup: predicts normal startup buffering rather than playback freeze;
- Include current rebuffering: event has already happened;
- Treat unknown as playing: creates unsupported labels.

### Outcome

```text
10,877,668 eligible rows
4,826 currently rebuffering rows excluded
955,982 unknown-state rows excluded
```

---

## D-004: Preserve natural class prevalence in partitioned Parquet

**Date:** 2026-07-26  
**Status:** Accepted  
**Stage:** Dataset construction

### Context

The raw sent table has 11.9 million rows and only 2,851 eligible positive rows.
Equal positive/negative sampling would create an artificial event rate.

### Decision

- Preserve all eligible positive and negative rows;
- save 24 Snappy Parquet parts;
- process incrementally.

### Outcome

The processed dataset is approximately 0.36 GB and can be reused without rescanning
the 1.74 GB raw sent CSV for every model.

---

## D-005: Split by session, not row or stream

**Date:** 2026-07-26  
**Status:** Accepted  
**Stage:** Validation

### Context

Adjacent rows from a session share a TCP connection and playback history. A session
can contain multiple streams after channel switches.

### Decision

Use `session_id` as the outer split group. Preserve an 80/20 development/test split
with no overlap and coarse stratification by positive volume.

### Outcome

```text
Development：2,765 sessions, 8,648,637 rows, 2,190 positives
Test：          692 sessions, 2,229,031 rows,   661 positives
Overlap：0
```

### Interpretation

80/20 is a practical allocation, not a universal rule. The five positive-volume
strata are not CV folds.

---

## D-006: Freeze the simple baseline at `buffer < 1 second`

**Date:** 2026-07-26  
**Status:** Accepted  
**Stage:** Baseline

### Context

Several buffer cutoffs illustrate the Precision–Recall trade-off, but choosing the
best-looking test cutoff would overfit.

### Decision

Use `buffer < 1.0` as the fixed rule baseline. Other cutoffs are development-only
sensitivity analysis.

### Development Outcome

```text
Precision：46.07%
Recall：17.40%
FPR：0.0052%
Alert rate：0.0096%
```

---

## D-007: Use a fixed, interpretable incremental Logistic V1

**Date:** 2026-07-27  
**Status:** Accepted  
**Stage:** Modelling

### Decision

Use StandardScaler plus L2-regularized SGD logistic regression with nine numeric
sent-time features. Do not use class weighting, negative downsampling, future ACK,
automatic polynomial interactions, Wald-test selection or test-driven tuning.

### Reason

- Fits 8.6 million development rows incrementally;
- preserves natural prevalence;
- is explainable;
- provides a strong baseline before adding nonlinear models.

### Outcome

The strongest standardized coefficients were:

```text
cum_rebuf +0.479
buffer    -0.405
```

Delivery rate was +0.006, close to zero and not interpreted causally.

---

## D-008: Use AP as the primary frozen-test metric; do not select a test threshold

**Date:** 2026-07-28  
**Status:** Accepted  
**Stage:** Evaluation

### Context

Test prevalence is 0.029654%. Accuracy would be approximately 99.97% for an
all-negative model and is therefore misleading.

### Decision

Use Average Precision to evaluate row-level risk ranking. Compare with random
prevalence and continuous buffer-only ranking.

### Outcome

```text
Random AP：       0.0002965
Buffer-only AP： 0.3616017
Logistic V1 AP： 0.5477129
```

The model improves AP over buffer only by 0.1861 absolute and 1.51x relative.

### Boundary

No Logistic probability threshold was selected. AP is a score, not a tuned
parameter and not Recall. Future threshold selection must use development
validation and a new untouched evaluation set/date.

