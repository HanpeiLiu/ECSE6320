"""Read-only follow-up after detecting the POSIX AIO per-process depth ceiling."""
import json,random,sys
from pathlib import Path
from run import P,GIB,TRIALS,run_fio
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'shared'))
from common import write_json,now
cases=[]
for jobs in [2,4,8,12]:
    cases.append(dict(id=f'parallel-randread-b4096-q8-jobs{jobs}',rw='randread',bs=4096,qd=8,numjobs=jobs,
                      size=GIB,io_bytes=4*GIB,runtime='2s',suites=['parallelism'],partition_bytes=(GIB//jobs//4096)*4096))
write_json(P/'config/parallelism-plan.json',dict(created_utc=now(),reason='Single-process QD>=32 gave mean in-flight requests ~16. These read-only forked workers test beyond that host-engine limit.',
                                             trials=TRIALS,cases=cases))
for trial in range(TRIALS):
    order=cases.copy();random.Random(36320+trial).shuffle(order)
    for c in order:
        run_fio(c,trial,extra=dict(numjobs=str(c['numjobs']),thread='0',size=str(c['partition_bytes']),offset_increment=str(c['partition_bytes'])))
        print(f'Parallel read trial {trial+1}: {c["numjobs"]} jobs',flush=True)
