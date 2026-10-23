# Workload source

Project3 uses the upstream FIO engine rather than a new I/O implementation. The project's source is in ../scripts/: run.py constructs and validates every workload, parallelism.py controls separate processes/ranges, and analyze.py parses full JSON+ records and creates figures/report. Exact generated workload source is in ../config/generated/*.fio.

FIO's pinned source URL, commit and version are in ../../tools/manifest.json; ../../tools/bootstrap.py and rebuild.py retrieve and compile it locally. This keeps source and measurement semantics reproducible without copying an unversioned binary into the submission.
