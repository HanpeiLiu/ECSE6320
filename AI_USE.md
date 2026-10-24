# AI-use disclosure

OpenAI Codex assisted with experiment design, C/Python code, configuration, debugging, data processing, plots and report writing. The agent executed real measurements, reference/sanity checks and compiler/disassembly inspection; unavailable facilities were not replaced with invented results.

- **P1:** all primary references and324 boundary cases passed. A compute pilot was rejected after only9 of16 assumed FMAs survived compilation; the corrected loop verifies16. Ordinary dot partially vectorized despite the initial hypothesis; a separate volatile-accumulator control verified the explicit no-vectorization case.
- **P2:** pointer cycles and read/write schedules were checked.42 real PMU traces were captured; page-offset and63/64-load unroll controls were added. The failed superpage request, tiny-cycle anomaly and poor approximate-AMAT fit are retained and discussed.
- **P3:** dedicated-file CRC32C validation, I/O-error checks and a cumulative write ledger were used. Longer read-only tails and forked-process controls followed the initial results. The large tail outlier remains; its cause is not asserted.

The student has not yet independently reviewed these artifacts; understanding, validation and explanation remain the student's responsibility before submission. The three-project report contains the hypotheses, negative cases, anomalies and limitations; supporting records remain inside each project.
