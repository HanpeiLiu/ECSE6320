"""Controls for page-offset aliasing and unusually fast tiny pointer cycles."""
from pathlib import Path
import itertools,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import command,write_json,now
from profile_counters import capture
P=ROOT/'project2';rows=[]
for unroll in [63,64]:
    r=command(['clang','-O3','-mcpu=native','-ffp-contract=off','-g',f'-DCHASE_UNROLL={unroll}',P/'src/memory_variants.c','-o',P/f'build/memory-u{unroll}'])
    write_json(P/f'evidence/build-u{unroll}.json',r)
    if r['returncode']:raise RuntimeError(r)
    d=command(['xcrun','llvm-objdump','--disassemble',P/f'build/memory-u{unroll}'])
    (P/f'evidence/unroll-{unroll}-disassembly.txt').write_text(d['stdout'])
for trial,unroll,nodes in itertools.product(range(3),[63,64],[64,128,256]):
    r=command([P/f'build/memory-u{unroll}','chase',str(nodes*128),'128','random','.12',str(6320+trial)])
    if r['returncode']:raise RuntimeError(r)
    m=json.loads(r['stdout']);m.update(trial=trial,unroll=unroll,study='tiny_cycle');rows.append(m)
    write_json(P/f'data/raw/followup/tiny-n{nodes}-u{unroll}-r{trial}.json',r)
cases=[]
for nodes in [256,4096,16384]:
    cases.append(dict(id=f'tlb-balanced-nodes{nodes}',executable=str(P/'build/memory-u64'),args=['chase',str(nodes*16384),'16384','balanced','1.2','6320'],kernel='chase_batch',suite='TLB-balanced',bytes=nodes*16384,spacing=16384,nodes=nodes))
write_json(P/'config/followup-plan.json',dict(created_utc=now(),reason='Offset-zero page-spread case can alias L1 cache sets. Balance page offsets across 128 line positions; retain original data. Also compare 63/64-load unroll for tiny cycles.',cases=cases,plain_trials=5,counter_trials=3))
for c,trial in itertools.product(cases,range(5)):
    args=[P/'build/memory-u64','chase',str(c['bytes']),'16384','balanced','.12',str(6320+trial)]
    r=command(args);write_json(P/f'data/raw/followup/{c["id"]}-r{trial}.json',r)
    if r['returncode']:raise RuntimeError(r)
    m=json.loads(r['stdout']);m.update(trial=trial,study='balanced_pages');rows.append(m)
import pandas as pd
pd.DataFrame(rows).to_csv(P/'data/processed/followup.csv',index=False)
for trial,c in itertools.product(range(3),cases):
    capture(c,trial,P/'data/raw/counters')
    print(f'Balanced-page PMU trial {trial+1}: {c["nodes"]} nodes',flush=True)
