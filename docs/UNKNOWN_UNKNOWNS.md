# UNKNOWN_UNKNOWNS.md

## U-001: Exact timing of buffer measurements

**Status:** Partly resolved; limitation remains

### What We Learned

Puffer documents `video_sent.buffer` and `cum_rebuf` as the server's last recorded
client values, updated when relevant client/ACK messages arrive. They are available
at prediction time but may be stale.

### Remaining Unknown

How much reporting lag exists at each sent row, and whether lag varies with network
or browser state.

### Impact

Can weaken calibration and make high-buffer `rebuffer` rows appear contradictory.

### Required Future Test

Measure age since `client_event_time` and evaluate model performance by measurement
staleness.

---

## U-002: Session dependence and effective sample size

**Status:** Detected and partly controlled

### What We Learned

Rows are highly concentrated:

```text
Top 1 session：17.75% of development positive rows
Top 5：44.48%
Top 10：58.05%
```

Train/test are separated by session, overlap is zero.

### Remaining Unknown

The uncertainty interval around AP after accounting for session-level dependence.

### Required Future Test

Cluster/session bootstrap of test AP or evaluation across multiple independent
dates.

---

## U-003: Right censoring near stream or data boundaries

**Status:** Open

### Missing Knowledge

A sent row near the final observed point may receive `target_5s=0` because the
stream or daily file ends before a full five-second future window is observed.

### Why It Matters

Some negatives may be unknown rather than true negatives.

### Required Future Test

Require at least five seconds of observable stream follow-up or explicitly mark
censored rows.

---

## U-004: Row-level recall versus freeze-event recall

**Status:** Open

### Missing Knowledge

One freeze can create several positive sent rows. Row-level AP does not say how many
distinct freeze episodes receive at least one timely warning.

### Why It Matters

Operationally, one warning before an event may be enough even if several other
positive rows were missed.

### Required Future Test

Link positive rows to `freeze_start_time` and calculate:

```text
event detected = at least one alert in the five seconds before a freeze
```

---

## U-005: Probability calibration

**Status:** Open

### Evidence

```text
Test prevalence：0.029654%
Mean predicted probability：0.041735%
Maximum prediction：99.99874%
```

### Missing Knowledge

Whether predicted probabilities correspond to observed frequencies across risk
bins and sessions.

### Required Future Test

Calibration curve, Brier score, log loss and inspection of extreme predictions,
without choosing a threshold from the existing test.

---

## U-006: Cross-date and experiment generalisation

**Status:** Open

### Missing Knowledge

Whether V1 remains useful on a different day, ABR experiment, congestion-control
scheme or content mix.

### Why It Matters

The current test is session-held-out but comes from the same daily dataset as
development.

### Required Future Test

Use a later untouched Puffer date as the true external evaluation set and report
performance by `expt_id`/ABR subgroup.

---

## U-007: Nonlinear and interaction structure

**Status:** Open; not required for V1

### Evidence

Within sufficiently populated buffer bands, higher delivery rate generally
corresponded to lower positive rate, but its additive logistic coefficient was
close to zero and positive.

### Candidate Mechanisms

```text
size / delivery_rate
buffer - size / delivery_rate
rtt - min_rtt
in_flight / cwnd
```

### Required Future Test

Predeclare a small V2 feature set, compare it with V1 using development CV, then
evaluate on a new untouched date. Do not generate every polynomial interaction
blindly.

