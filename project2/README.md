# Project 2 — how to inspect and reproduce

Read [REPORT.md](REPORT.md), [HYPOTHESES.md](HYPOTHESES.md), and [AI_USE.md](AI_USE.md). There are 355 primary timing rows (71×5), 33 supplementary timing controls and 42 independent hardware-counter captures (14×3).

From the **repository root**, with .venv active:

```sh
python project2/scripts/analyze.py
```

This regenerates all tables, figures and the report using existing raw records. Units and provenance are defined in ../DATA_DICTIONARY.md. `data/raw/counters/` preserves full original traces, XML and leaf-kernel attribution metadata. Compressed traces must be retained, although they make this project roughly 0.8GB.

For a full separate recollection use root run_all.py --collect-to. After Project 1 executables exist, the relevant sequence is:

```sh
python project2/scripts/run.py
python project2/scripts/profile.py
python project2/scripts/followup.py
python project2/scripts/analyze.py
```

run.py compiles the primary benchmark, checks cycle and read/write correctness, explicitly probes superpage support, then runs seeded pointer-chase, traffic/probe, granularity, mix, intensity and page-locality sweeps. Its default plain batch is120ms and five trials. The manual Instruments counter template is saved at evidence/ECSE6320-Counters.tracetemplate; capture/export is automated by shared/profile_counters.py. It uses a byte-identical executable at a temporary path without spaces, then preserves the original trace before cleanup. Real counters require a compatible Apple CPU/Xcode, Instruments profiling permission and available events. Recheck event availability on another machine.

followup.py builds memory_variants.c with63/64 dependent-load unroll factors and balanced page offsets, preserving separate data for both controls. Original primary source is memory.c; the supplementary source-name change is explained by evidence/followup-source-provenance.json. The default study uses up to256MiB plus a64MiB loaded read probe. Source-level traffic includes8B operations with additional index/control overhead, so these kernels do not establish physical DRAM peak bandwidth.

16KiB pages are native. The real2MiB superpage probe failed on this host. No separate traditional L3, 4KiB-page mode, fixed clock, hard core pinning or NUMA placement is claimed. These are documented platform limits, not replaced by simulated results.
