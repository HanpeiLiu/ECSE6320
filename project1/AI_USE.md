# AI-use and validation note

OpenAI Codex generated and revised benchmark code, automation, plots, and this report.
The agent ran reference/sanity checks and inspected real compiler output and measurement records.
No result was invented to replace an unavailable hardware facility.
The student has not yet independently reviewed these artifacts; that review and explanation remain required before submission.
Installation checks and pilot runs are distinguished from final experiments.
See `project1/data/raw/` for exact commands, raw outputs, failures, and environment records.

## Specific validation and revisions

The agent checked 324 boundary cases plus all primary references. A compute-peak pilot was rejected after disassembly showed only 9 of 16 assumed FMAs; its records are retained. A corrected loop verified all16 FMAs. The ordinary strict dot hypothesis was partly falsified: vector products coexist with scalar ordered accumulation. Thirty additional volatile-accumulator control jobs and targeted disassembly verify an explicit non-vectorized negative case.
