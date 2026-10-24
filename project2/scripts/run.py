from pathlib import Path
import itertools,json,random,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import command,write_json,environment,now
P=ROOT/'project2';TRIALS=5;DURATION=.12
def make_plan():
    cases={}
    def add(suite,mode,**kw):
        key=mode+'-'+'-'.join(f'{k}{v}' for k,v in kw.items())
        if key not in cases:cases[key]=dict(id=key,mode=mode,**kw,suites=[])
        if suite not in cases[key]['suites']:cases[key]['suites'].append(suite)
    for size,pattern in itertools.product([16384,65536,131072,262144,1048576,4194304,16777216,33554432,67108864,268435456],['sequential','random']):
        add('baseline_workingset','chase',bytes=size,spacing=128,pattern=pattern)
    for size,spacing,pattern in itertools.product([65536,268435456],[64,256,1024],['sequential','random']):
        add('granularity','chase',bytes=size,spacing=spacing,pattern=pattern)
    for spacing,pattern,pct in itertools.product([64,256,1024],['sequential','random'],[0,50,70,100]):
        add('pattern_granularity_rw','traffic',bytes=268435456,spacing=spacing,pattern=pattern,readpct=pct,threads=1,probe_bytes=67108864)
    for threads in [1,2,4,6,8,12]:
        add('intensity','traffic',bytes=268435456,spacing=64,pattern='sequential',readpct=100,threads=threads,probe_bytes=67108864)
    add('intensity_zero','chase',bytes=67108864,spacing=128,pattern='random')
    add('pitfall_cache_reuse','traffic',bytes=65536,spacing=64,pattern='sequential',readpct=100,threads=1,probe_bytes=67108864)
    for nodes,spacing in itertools.product([64,256,1024,4096,16384],[128,16384]):
        add('page_locality','chase',bytes=nodes*spacing,spacing=spacing,pattern='random')
    return list(cases.values())

def args_for(c,duration=DURATION,seed=6320):
    if c['mode']=='chase':return [P/'build/memory','chase',str(c['bytes']),str(c['spacing']),c['pattern'],str(duration),str(seed)]
    return [P/'build/memory','traffic',str(c['bytes']),str(c['spacing']),c['pattern'],str(c['readpct']),str(c['threads']),str(duration),str(seed),str(c['probe_bytes'])]

def main():
    (P/'build').mkdir(exist_ok=True)
    r=command(['clang','-O3','-mcpu=native','-ffp-contract=off','-g','-Wall','-Wextra',P/'src/memory.c','-o',P/'build/memory'])
    write_json(P/'evidence/build.json',r)
    if r['returncode']:raise RuntimeError(r)
    for test in ['selftest','hugepage']:
        r=command([P/'build/memory',test]);write_json(P/f'evidence/{test}.json',r)
        if r['returncode']:raise RuntimeError(r)
    cases=make_plan();write_json(P/'config/plan.json',dict(created_utc=now(),trials=TRIALS,target_seconds=DURATION,seed=6320,cases=cases))
    write_json(P/'data/raw/environment-before.json',environment('project2'))
    rawdir=P/'data/raw/runs';rawdir.mkdir(exist_ok=True);rows=[]
    for trial in range(TRIALS):
        order=cases.copy();random.Random(16320+trial).shuffle(order)
        for idx,c in enumerate(order):
            path=rawdir/f'{c["id"]}-r{trial}.json'
            if path.exists():
                saved=json.loads(path.read_text())
                if saved['returncode']==0 and 'measurement' in saved:rows.append(saved['measurement']);continue
            r=command(args_for(c,seed=6320+trial),timeout=90)
            if r['returncode']==0:
                m=json.loads(r['stdout']);m.update(case_id=c['id'],trial=trial,suites=';'.join(c['suites']),started_utc=r['started_utc'])
                r['measurement']=m;rows.append(m)
            write_json(path,r)
            if r['returncode']:raise RuntimeError(f'Case failed: {path}')
            if idx%15==0:print(f'Project 2 trial {trial+1}/{TRIALS}: {idx+1}/{len(cases)}',flush=True)
    import pandas as pd
    pd.DataFrame(rows).to_csv(P/'data/processed/measurements.csv',index=False)
    write_json(P/'data/raw/environment-after.json',environment('project2'))
    print(f'Project 2 complete: {len(rows)} measurements.',flush=True)
if __name__=='__main__':main()
