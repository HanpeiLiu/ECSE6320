# Pre-experiment hypotheses

Recorded before the project measurements.

1. Increasing application-side outstanding I/O should raise 4KiB random-read throughput until
   a knee; beyond that point latency/tail latency should grow faster than throughput.
2. Larger sequential blocks should improve useful byte throughput; larger random blocks may
   reduce IOPS while increasing transferred bytes/s.
3. Read/write mixes should differ from pure reads and pure writes. Write completion without
   per-request flush is not equivalent to durable storage latency.
4. Buffered reads of a small reused file may measure page cache rather than the SSD.
5. Short repeated runs measure burst/current-state behavior, not vendor-certified steady state
   or SLC exhaustion. Large destructive preconditioning is intentionally outside this small-data study.

Use only a new project-owned regular file, never a raw device. Fixed incompressible FIO data
pattern, documented file ranges, alignment, direct setting, engine, effective depth distribution,
repetitions, latency percentiles and sample counts are retained. Read-only SMART snapshots track
temperature and write counters. The runner enforces a cumulative test-write budget.
