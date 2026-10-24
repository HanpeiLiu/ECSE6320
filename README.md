# ECSE 4320/6320 - Class projects

`REPORT.pdf` combines the three projects, including hypotheses, validation, negative cases and limitations. `AI_USE.md` discloses AI assistance. All code, scripts, configurations, raw/processed data, plots and evidence are inside the corresponding `project1/`, `project2/` or `project3/` directory.

## Environment

M3 Pro, 6 performance + 6 efficiency cores (12 physical/logical; no SMT), 18GB; macOS15.6.1; Xcode26.3 / Apple Clang17.0.0; Python3.12.8. NEON128-bit, 128B cache lines, 16KiB pages. P-core L1D128KiB/shared L2 16MiB; E-core L1D64KiB/shared L2 4MiB. SSD: APPLE SSD AP1024Z (~1TB), Apple Fabric/APFS. Collection used AC power, dynamic frequency and user-initiated QoS; no hard affinity/isolation or NUMA control. Exact flags, tool versions and historical system snapshots are retained in each project's raw data/evidence.

## Reproduce

The existing environment is hidden at `.venv/`. On a fresh compatible Mac with Xcode:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r project1/scripts/requirements.txt
```

Regenerate tables/plots from saved raw data and check completeness/integrity, without benchmark writes:

```sh
.venv/bin/python project1/scripts/reproduce.py
```

To regenerate the combined PDF:

```sh
.venv/bin/python -m pip install -r project1/scripts/requirements-report.txt
.venv/bin/python project1/scripts/report.py
```

For a new collection, build the pinned local tools, then use a new output directory. The SSD workload requires explicit write opt-in:

```sh
.venv/bin/python project1/scripts/bootstrap_tools.py
.venv/bin/python project1/scripts/reproduce.py --collect-to ../new-results --allow-ssd-writes
```

Run sequentially on AC power with other activity minimized. Rebuild the report inside the new directory afterward. P2 counters require compatible Instruments/PMU access and use the P1 native executable for numeric-loop profiles. `.venv/`, local `.tools/`, caches and disposable/build files are excluded from Git.

## Files and interpretation

- `src/` and `scripts/`: implementation/build/run/analysis; P3 uses upstream FIO and Python scripts. `config/`: plans, preserved pre-experiment hypotheses, pinned tools and generated FIO workloads.
- `data/raw/`: exact commands, output, environment and measurements; P2 includes original PMU traces/XML; P3 includes JSON+, SMART and write ledger. `data/processed/` and `figures/`: complete derived tables/plots. `evidence/`: correctness, compiler/disassembly, support probes and provenance. Include-path-only source relocation is documented here; historical raw paths/hashes remain unchanged.
- P1 has 1,200 primary rows plus 324 boundary checks/30 negative controls; P2 has 355 primary rows/33 extra timings/42 PMU captures; P3 has 141 performance jobs plus 2 preparation jobs. Repeats5/5/3; plots use median/sample SD, with individual tail trials and min-max. Combined audit: `project1/evidence/audit.json`; per-project `evidence/SHA256SUMS` uses repository-relative paths.
- Useful bytes are not physical bus traffic. GiB/MiB use2^30/2^20 bytes. P2 probe latency measures loaded reads. P3 mixed jobs have two direction rows with duplicated aggregate fields; deduplicate case/trial before summing totals. Total and completion latency differ; directional percentiles are not averaged. Little's Law estimates application concurrency.

P3 used owned disposable files only: 1GiB main/64MiB verification,104GiB write cap, 53.375GiB recorded payload writes. No forced steady state, persistence-per-write, physical LBA or link-ceiling claim is made. Superpages failed; no native4KiB-page or separate-L3 result is fabricated. GPU is optional and omitted. Repository: https://github.com/HanpeiLiu/ECSE6320. Student independent review remains required.
