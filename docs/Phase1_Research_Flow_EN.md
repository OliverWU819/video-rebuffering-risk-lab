# Video Rebuffering Risk Lab — Phase 1: Target and State Reconstruction

> **Status:** Complete. This document contains the target construction used by the
> final modelling pipeline. The early cumulative-counter approach is retained only
> as a rejected method.

## 1. Research question

> Can telemetry available when a server sends a video chunk predict whether the
> same stream will begin rebuffering within the next five seconds?

Each `video_sent` row is a prediction opportunity.

```text
target_5s = 1
if a rebuffer event begins in the same stream strictly after sent_time
and no more than five seconds later
```

The exact timing rule is:

```text
0 < freeze_start_time - sent_time <= 5 seconds
```

## 2. Data source and table semantics

The project uses public Stanford Puffer telemetry covering
`2026-07-19T11_2026-07-20T11`.

### `video_sent`

One row represents a video chunk sent by the server. It supplies the prediction
timestamp and V1 features.

### `client_buffer`

One row is a periodic or event-driven client playback report. It is the
authoritative source for playback state and freeze labels.

### `video_acked`

One row records the later acknowledgement of a chunk. ACK information can support
retrospective analysis, but future ACK time is unavailable at prediction time and
is therefore excluded from V1.

Puffer defines:

```text
session: session_id
stream:  session_id + index
```

A channel switch creates a new stream index while retaining the same session and
TCP connection.

## 3. The label correction that changed the project

### 3.1 Rejected approach

The first attempt inferred freeze start from:

```python
cum_rebuf_change > 0
```

That sounded reasonable: if cumulative rebuffer time increased, perhaps a freeze
had just begun.

It was wrong.

A manually reconstructed ±2-second timeline showed:

```text
rebuffer row:
buffer is nearly exhausted, but cum_rebuf has not yet increased

later play row:
playback resumes, buffer has recovered, and cum_rebuf increases
```

The cumulative counter can therefore update near the end of a freeze. Treating its
increase as the start can label a resume as a freeze onset.

### 3.2 Authoritative approach

Puffer explicitly defines:

- `rebuffer`: the client begins rebuffering;
- `play`: the client resumes after rebuffering;
- `startup`: initial playback begins;
- `init`: a new channel/stream begins;
- `timer`: a periodic status report.

The final rule is:

```python
freeze_start = client_buffer["event"] == "rebuffer"
```

This decision is simpler, documented by the data publisher and supported by the
manual timeline.

## 4. Full freeze-event audit

Chunked scanning of the complete `client_buffer` file found:

```text
Freeze starts:                         5,935
Streams with at least one freeze:        671
Duplicate freeze keys:                     0
```

Buffer recorded at freeze start:

```text
median: 0.078 s
90%:    below 0.574 s
95%:    below 1.281 s
99%:    below 1.872 s
max:    3.826 s
```

High-buffer `rebuffer` rows were retained. They may reflect reporting lag,
server/client timing differences or genuine edge cases. Removing them simply
because they look inconvenient would make the label rule subjective.

## 5. Reconstructing playback state

Four event types define state transitions:

```text
init      -> startup_buffering
startup   -> playing
rebuffer  -> rebuffering
play      -> playing
```

Full extraction counts:

```text
init:      34,766
startup:   34,106
rebuffer:   5,935
play:       5,600
total:     80,407
```

Puffer's `play` is a legacy label whose operational meaning is closer to
`resume`.

The state-event table is stored locally as:

```text
data/interim/playback_state_events.parquet
```

## 6. Prediction eligibility

The model predicts only when the most recently known playback state is `playing`.

```python
eligible_prediction = playback_state == "playing"
```

Excluded rows:

- `startup_buffering`: initial startup delay is not a mid-playback freeze;
- `rebuffering`: the event has already happened;
- `unknown`: no reliable earlier client state is available.

For every sent row:

1. a backward as-of join finds the latest earlier playback-state event;
2. a forward as-of join finds the next freeze start in the same stream;
3. the five-second timing rule creates `target_5s`.

## 7. Full labelled dataset

The raw sent CSV was processed in 500,000-row chunks and saved as 24 partitioned
Parquet files.

```text
All sent rows:                    11,900,686
Eligible playing rows:            10,877,668
Positive target rows:                  2,851
Rows currently rebuffering:             4,826
Rows with unknown state:              955,982
Partitioned Parquet size:               0.36 GB
```

Output:

```text
data/processed/labelled_sent_5s/
```

All natural negative rows were retained. The pipeline did not create an artificial
50/50 class balance.

## 8. Timing and leakage audit

In an initial 500,000-row label check, 714 positive rows had:

```text
minimum seconds_until_freeze: 0.001
median:                       2.064
99th percentile:             4.948
maximum:                      4.986
```

No positive label occurred before its sent time or beyond the five-second horizon.

V1 does not use:

- future ACK time;
- `freeze_start_time`;
- `seconds_until_freeze`;
- future buffer reports;
- the target itself.

Puffer states that `buffer` and `cum_rebuf` in `video_sent` are the server's last
recorded client values. They can be stale, but they are already known at prediction
time and therefore are not direct look-ahead leakage.

## 9. Superseded Phase 1 results

An earlier research note reported:

- 5,541 inferred episodes;
- 536 affected streams;
- 75.92% five-second episode coverage;
- ACK-before/after-freeze statistics based on those episodes;
- pre-freeze buffer-decline statistics based on those episodes.

Those values came from the rejected cumulative-counter definition. They are useful
as a record of the debugging process but are not part of the final evidence chain.
Any future ACK or event-level analysis must be recomputed from the authoritative
5,935 `rebuffer` events.

## 10. Phase 1 conclusion

Phase 1 established that:

1. a `video_sent` row is a defensible prediction opportunity;
2. the explicit `rebuffer` event is safer than inferring onset from a cumulative
   counter;
3. playback state must separate startup, playing, rebuffering and unknown rows;
4. the label can be expressed with a strict forward five-second window;
5. the dataset is large enough to require chunked CSV-to-Parquet processing;
6. the target is extremely imbalanced;
7. model validation must isolate sessions, not randomly split rows.

The reusable reasoning pattern is:

```text
Question
-> table
-> key
-> time direction
-> eligibility
-> label
-> audit
-> conclusion
```

## References

- [Puffer Data Description](https://puffer.stanford.edu/data-description/)
- [Puffer source repository](https://github.com/StanfordSNR/puffer)
- [Puffer paper](https://puffer.stanford.edu/static/puffer/documents/puffer-paper.pdf)

