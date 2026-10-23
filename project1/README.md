# Project 1 — how to inspect and reproduce

Read [REPORT.md](REPORT.md), [HYPOTHESES.md](HYPOTHESES.md), and [AI_USE.md](AI_USE.md). The primary collection has 240 unique configurations × 5 trials. Three required kernels are AXPY, multiply and stencil; ordinary dot and a volatile-accumulator control are additional negative experiments.

From the **repository root**, with .venv active:

```sh
python project1/scripts/analyze.py
```

This rebuilds processed tables and figures from saved raw JSON. No benchmark is rerun. The full record map and units are in ../DATA_DICTIONARY.md. Compiler reports and complete disassembly are under evidence/; the report contains concise excerpts and selected quantitative tables.

For a separate full recollection, use the root run_all.py --collect-to workflow so the submitted dataset is preserved. Its Project 1 sequence is:

```sh
python project1/scripts/run.py
python project1/scripts/finalize_validation.py
python project1/scripts/negative.py
python project1/scripts/analyze.py
```

The run script builds scalar/auto/native executables using scripts/build.py, records environment, runs reference-checked measurements and STREAM/compute references. finalize_validation.py requires exactly 16 float32 FMA instructions in the compute loop before accepting its 128-FLOP iteration count, then runs 324 tiny correctness checks. negative.py checks both reference results and absence of vector arithmetic in the deliberately constrained loop. The already collected 30 negative-control rows are additional to the 1,200 primary rows.

Default batch target30ms; five reproducibly shuffled trials; initialized/aligned arrays and pre-timing correctness/warmup. Primary sizes range from 1,024 to 16,777,216 elements; special tail cases are smaller. Largest active extents are needed to exceed local caches, and all required kernels remain single-threaded. No fixed frequency or hard affinity is claimed.
