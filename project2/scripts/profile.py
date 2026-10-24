from pathlib import Path
import itertools,sys,json,plistlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import write_json,now
from profile_counters import capture
P=ROOT/'project2'
cases=[]
for size in [65536,4194304,268435456]:
    cases.append(dict(id=f'cache-chase-{size}',executable=str(P/'build/memory'),args=['chase',str(size),'128','random','1.2','6320'],kernel='chase_batch',suite='cache',bytes=size,spacing=128))
for nodes,spacing in itertools.product([256,4096,16384],[128,16384]):
    cases.append(dict(id=f'tlb-nodes{nodes}-spacing{spacing}',executable=str(P/'build/memory'),args=['chase',str(nodes*spacing),str(spacing),'random','1.2','6320'],kernel='chase_batch',suite='TLB',bytes=nodes*spacing,spacing=spacing,nodes=nodes))
for n in [8192,16777216]:
    cases.append(dict(id=f'numeric-mul-n{n}',executable=str(ROOT/'project1/build/native'),args=['mul','f32',str(n),'1','0','1.2'],kernel='mul_f32',suite='numeric_cache',n=n))
write_json(P/'config/counter-plan.json',dict(created_utc=now(),trials=3,cases=cases))
db=plistlib.load(open('/usr/share/kpep/as3.plist','rb'))['system']['cpu']
names=['L1D_CACHE_MISS_LD_NONSPEC','L1D_TLB_MISS_NONSPEC','L2_TLB_MISS_DATA','INST_SIMD_ALU']
write_json(P/'evidence/counter-event-definitions.json',{k:db['events'][k] for k in names})
results=[]
for trial in range(3):
    for i,c in enumerate(cases):
        results.append(capture(c,trial,P/'data/raw/counters'))
        print(f'PMU trial {trial+1}/3: {i+1}/{len(cases)} {c["id"]}',flush=True)
write_json(P/'data/processed/counter-summary.json',results)
