# AI-use and validation note

OpenAI Codex generated and revised benchmark code, automation, plots, and this report.
The agent ran reference/sanity checks and inspected real compiler output and measurement records.
No result was invented to replace an unavailable hardware facility.
The student has not yet independently reviewed these artifacts; that review and explanation remain required before submission.
Installation checks and pilot runs are distinguished from final experiments.
See `project3/data/raw/` for exact commands, raw outputs, failures, and environment records.

## Specific validation and revisions

The agent verified CRC32C on a dedicated file, checked all FIO I/O errors, kept a cumulative write ledger, extended read-only tail sampling, and tested forked processes after requested QD stopped matching actual concurrency. A large tail outlier was retained; GC was not asserted as its cause.
