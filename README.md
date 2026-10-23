# ECSE 4320/6320 class projects — collected results

Three experiments were run on this M3 Pro Mac on 2026-10-23. Start with each report:

| Project | Report | Recorded data |
| --- | --- | --- |
| 1 — SIMD | [Report](project1/REPORT.md) | 240 configurations × 5 trials = 1,200 primary rows; 324 boundary checks; 30 additional negative controls; 5 STREAM and 5 validated compute-ceiling runs |
| 2 — cache/memory | [Report](project2/REPORT.md) | 71 configurations × 5 trials = 355 primary rows; 33 supplementary timing controls; 42 real hardware-PMU captures |
| 3 — SSD | [Report](project3/REPORT.md) | 47 configurations × 3 trials = 141 performance runs; 2 preparation/verification jobs; 147 direction-specific rows |

[Requirement-by-requirement checklist](COMPLETENESS.md), [machine-readable checklist](REQUIREMENTS.csv), [data dictionary](DATA_DICTIONARY.md), [automated integrity audit](AUDIT.json).

Each project contains pre-experiment hypotheses, an AI-use note, source/scripts, full raw records, processed CSVs, figures and an English report. The supplied [assignment PDF](ECSE4320_6320_Class-wide_Projects.pdf) is the specification. No synthetic measurements fill unsupported platform features.

The examples are bounded: numeric arrays cross the CPU cache capacities; memory tests use up to 256MiB plus a 64MiB latency probe; SSD tests use a disposable 1GiB file. The SSD collector wrote **53.375GiB total**, including preparation, below its 104GiB enforced limit. A tiny cache-only case would fail to study DRAM; a tiny request count would not characterize p99.9 tails. Six read-only tail confirmations completed at least 123,209 requests each.

## Reproduce tables and plots without running hardware workloads

From this repository root:

```sh
source ./activate.zsh
python run_all.py
```

This reparses retained raw records, regenerates tables/reports/plots, and checks coverage and data consistency. It performs no SSD benchmark writes. Dependencies are pinned in requirements.txt; Python is installed in **.venv/**, which Finder hides by default (Command–Shift–Period). On a fresh compatible Mac:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Original absolute paths and transient executable staging paths are retained as provenance; scripts locate the current repository from their own file path. Do not edit original JSON to “fix” paths.

## Recollect experiments in a separate directory

Apple Silicon/macOS with Xcode and its license accepted is required for these native benchmarks and Instruments counter template. Tool versions, pinned upstream commits, checksums and build instructions are in tools/manifest.json. System Xcode is the official Apple tool; other executables remain under this repository.

```sh
python tools/bootstrap.py --build
python run_all.py --collect-to ../ecse6320-new-results --allow-ssd-writes
```

The destination must not exist. The runner copies the experiment recipe, preserves these results, uses the current local tools, runs workloads sequentially, then analyzes and audits the new collection. It intentionally requires a separate flag to start the bounded SSD writing workload. A standalone copy on another Mac can fetch/rebuild the local tools using bootstrap.py. PMU event availability/template compatibility must be rechecked if hardware or Xcode differs.

Individual instructions are in project1/README.md, project2/README.md and project3/README.md. Avoid concurrent benchmarking, use AC power, and minimize other work. No strict affinity, fixed frequency, or background-process isolation is claimed.

## Interpretation and remaining submission steps

macOS uses 16KiB pages here. The explicit 2MiB superpage allocation failed; there is no fabricated 4KiB/huge-page comparison. No separately exposed traditional L3, physical APFS LBA layout, or numerical Apple Fabric link ceiling was available. These limitations and observed anomalies are discussed in the reports. GPU/CUDA is optional and was omitted.

The local repository contains the submission materials. **GitHub upload is pending a destination repository and visibility choice.** No remote is configured. The largest retained file is below GitHub's 100MiB per-file limit; the complete raw PMU traces make the dataset roughly 0.8GB. Data/evidence must accompany a submission; do not submit only the figures. SHA256SUMS checks file integrity.

AI assisted code, experiment design, validation and report writing. The student must independently review, understand and be able to explain the work before submission; no such human review is claimed to have happened.
