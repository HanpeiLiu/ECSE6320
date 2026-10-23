# AI-use and validation note

OpenAI Codex generated and revised benchmark code, automation, plots, and this report.
The agent ran reference/sanity checks and inspected real compiler output and measurement records.
No result was invented to replace an unavailable hardware facility.
The student has not yet independently reviewed these artifacts; that review and explanation remain required before submission.
Installation checks and pilot runs are distinguished from final experiments.
See `project2/data/raw/` for exact commands, raw outputs, failures, and environment records.

## Specific validation and revisions

The agent checked unique pointer cycles and read/write mixes, captured42 real PMU traces, and added page-offset and63/64-load-unroll controls after seeing confounding behavior. The failed superpage allocation and poor approximate-AMAT fit were kept. No underlying architectural cause was invented for the tiny-cycle anomaly.
