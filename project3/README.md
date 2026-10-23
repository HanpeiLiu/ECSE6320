# Project 3 — how to inspect and reproduce

Read [REPORT.md](REPORT.md), [HYPOTHESES.md](HYPOTHESES.md), and [AI_USE.md](AI_USE.md). The dataset contains47 configurations ×3 trials =141 performance jobs, plus2 preparation jobs. Direction-specific CSV has147 rows because mixed jobs contribute separate read/write rows.

From the **repository root**, with .venv active:

```sh
python project3/scripts/analyze.py
```

This only parses retained JSON+, rebuilds tables/figures/report and performs no benchmark writes. See ../DATA_DICTIONARY.md for duplicate aggregate fields in mixed read/write rows, total versus completion latency, units, Little's Law and histogram conventions.

Every job has an exact configuration under config/generated/, a full JSON+ result, metadata with command/health snapshots and a write ledger. Main plan41×3; adaptive mid/knee-tail confirmations2×3; read-only parallel-process follow-up4×3. Each tail trial has at least123,209 completed requests.

To recollect, use the root run_all.py **--collect-to NEW_DIRECTORY --allow-ssd-writes** workflow. Project 3's sequence is scripts/run.py, scripts/parallelism.py, then scripts/analyze.py. These scripts may overwrite only their own disposable work/ssd-test.bin or verify.bin, require an ownership marker and regular files, and refuse arbitrary device paths. run.py verifies CRC32C on a64MiB file and initializes the1GiB main file before starting the matrix. Do not change the filename to a raw disk or existing valuable file.

The collector enforces104GiB cumulative payload writes, with worst-case reservations made before each job. Actual writes in this dataset are53.374626GiB including preparation. FIO is project-local3.43 using posixaio, aligned16KiB memory, fixed incompressible buffers, direct=1/F_NOCACHE except the labeled warm buffered-cache pitfall. Main jobs have both runtime and byte caps; there is no unlimited time-based write load.

This is a current-state/burst filesystem study. No device erase, full-drive preconditioning, deliberate SLC exhaustion or persistence-per-write claim is made. APFS physical LBAs and a standard PCIe ceiling are unavailable. Single-process requested QD32–256 achieves about16 average in-flight application requests; extra forked-process experiments test greater actual concurrency. Scripts keep these effects distinct from SSD hardware claims.
