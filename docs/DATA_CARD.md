# DATA_CARD.md

## Dataset Name

Stanford Puffer public streaming telemetry, daily release:
`2026-07-19T11_2026-07-20T11`.

## Source

Stanford Puffer research platform.

## Original Documentation

- https://puffer.stanford.edu/data-description/
- https://github.com/StanfordSNR/puffer
- https://puffer.stanford.edu/static/puffer/documents/puffer-paper.pdf

## Download Date

Not recorded in the current project. The data interval is not the download date and
must not be presented as one.

## Licence and Usage Conditions

Public research telemetry published by Puffer. Confirm the current Puffer terms and
course requirements before redistributing raw files. The project should distribute
code and metadata rather than republishing multi-GB raw data.

## Why This Dataset Fits the Project

The dataset links:

- server-side chunk sends;
- TCP/network telemetry;
- client playback state;
- explicit `rebuffer` events.

It therefore supports a timestamped, leakage-audited question about whether a
freeze begins within five seconds after a prediction opportunity.

## Raw Files

| File | Approx. size | Date range | Meaning |
|---|---:|---|---|
| `client_buffer_*.csv` | 8.06 GB | 2026-07-19T11 to 2026-07-20T11 UTC | Client state reports and playback events |
| `video_sent_*.csv` | 1.74 GB | Same | One server-side video-chunk send record |
| `video_acked_*.csv` | 1.12 GB | Same | Later acknowledgement observed by the server |

## Unit of Observation

Raw tables:

- `video_sent`: one row per video chunk sent by the server;
- `video_acked`: one row per video-chunk acknowledgement received by the server;
- `client_buffer`: one periodic or event-driven client playback report.

Modelling table:

> One eligible `video_sent` row while the reconstructed playback state is
> `playing`.

It is a prediction opportunity, not an independent user and not an independent
freeze episode.

## Session and Stream Identifiers

```text
session：session_id
stream： session_id + index
```

Puffer states that a channel switch creates a new stream index while retaining the
same session/TCP connection. Train/test isolation therefore uses the safer
session-level key.

## Time Fields

| Field | Meaning | Timezone | Precision |
|---|---|---|---|
| `sent_time` | Server sends a video chunk | UTC/GMT epoch | nanoseconds |
| `client_event_time` | Server receives a client state/event message | UTC/GMT epoch | nanoseconds |
| `freeze_start_time` | Time of client `rebuffer` report | UTC/GMT epoch | nanoseconds |
| ACK time | Server receives acknowledgement | UTC/GMT epoch | nanoseconds |

Server-observed timestamps and client state reports can have reporting delay. They
should not be treated as perfectly synchronized physical event times.

## Final Candidate Features

| Field | Meaning | Unit | Available at prediction time? |
|---|---|---|---|
| `buffer` | Last server-recorded playback buffer | seconds | Yes, possibly stale |
| `size` | Video chunk size | bytes | Yes |
| `ssim_index` | Chunk quality relative to canonical encode | unitless | Yes |
| `cwnd` | TCP congestion window | packets | Yes |
| `in_flight` | Unacknowledged packets in flight | packets | Yes |
| `min_rtt` | Minimum observed RTT | microseconds | Yes |
| `rtt` | Smoothed RTT estimate | microseconds | Yes |
| `delivery_rate` | TCP delivery-rate estimate | bytes/second | Yes |
| `cum_rebuf` | Last recorded cumulative rebuffer time in stream | seconds | Yes, possibly stale |

Excluded from V1 features:

- future ACK time and ACK delay;
- future `freeze_start_time`;
- `seconds_until_freeze`;
- target;
- future buffer reports;
- playback state indicating that rebuffering has already begun.

## Final Label

Authoritative freeze start:

```python
client_buffer["event"] == "rebuffer"
```

Row-level target:

```text
target_5s = 1 if
0 < freeze_start_time - sent_time <= 5 seconds
within the same session_id + index
```

`cum_rebuf` increments are not used to define freeze start because a manual
timeline showed that cumulative rebuffer time may update at the later `play/resume`
row.

## Playback-State Eligibility

```text
init      → startup_buffering
startup   → playing
rebuffer  → rebuffering
play      → playing
```

Only `playing` rows are eligible. Counts:

```text
All sent rows：               11,900,686
Eligible playing rows：       10,877,668
Currently rebuffering rows：       4,826
Unknown-state rows：             955,982
Positive eligible rows：           2,851
```

## Missingness and Invalid Numeric Values

Across the nine V1 features in 8,648,637 development rows:

```text
missing： 0
infinite：0
```

This is not a claim that every raw column in every raw table has no missing values.
Unknown playback state is handled separately and excluded from modelling.

## Duplicates

Final freeze-start extraction:

```text
Freeze starts：5,935
Duplicate (session_id, index, freeze_start_time)：0
```

## Processed Outputs

```text
data/interim/playback_state_events.parquet
data/processed/labelled_sent_5s/part_001.parquet ... part_024.parquet
data/processed/session_split.parquet
data/processed/development_cv_folds.parquet
```

Partitioned labelled dataset size: approximately 0.36 GB.

## Known Data-Collection Biases

- Puffer users and viewing conditions may not represent commercial short-video users;
- one day may contain unusual network, experiment or content conditions;
- ABR and congestion-control experiments affect feature distributions;
- client timer reports are not perfectly periodic;
- inactive browser tabs may delay reports;
- buffer/cumulative-rebuffer values in `video_sent` are last recorded values;
- stream endings create right-censoring risk;
- positive rows are highly concentrated in a small number of sessions.

## Privacy and Ethics

The released dataset uses anonymized session identifiers. Do not attempt user
re-identification. Operational actions such as lowering quality should be presented
as simulations because false alarms can unnecessarily degrade user experience.

## Limitations

- Single date;
- no external-date validation;
- row-level rather than event-level target evaluation;
- 955,982 unknown-state rows excluded;
- effective sample size is far smaller than row count;
- no proof that every high-buffer `rebuffer` report is physically synchronized;
- no complete right-censoring correction.

## Reproducible Processing

The raw CSVs are read in 500,000-row chunks. State events and freeze starts are
extracted once, then sent rows are labelled and saved as 24 Snappy-compressed
Parquet parts. The notebook containing the current pipeline is:

```text
notebooks/02_target_definition.ipynb
```

