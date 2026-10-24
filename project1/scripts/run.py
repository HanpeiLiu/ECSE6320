from pathlib import Path
import itertools,json,random,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import command,write_json,environment,power_state,now
P=ROOT/'project1';TRIALS=5
def make_plan():
    cases={}
    def add(suite,kernel,dtype,n,stride=1,offset=0):
        for build in ['scalar','auto','native']:
            key=f'{kernel}-{dtype}-n{n}-s{stride}-o{offset}-{build}'
            if key not in cases:cases[key]=dict(id=key,kernel=kernel,dtype=dtype,n=n,stride=stride,offset=offset,build=build,suites=[])
            if suite not in cases[key]['suites']:cases[key]['suites'].append(suite)
    for k,d,n in itertools.product(['axpy','mul','stencil'],['f32','f64'],[1024,8192,16384,65536,262144,1048576,4194304,16777216]):add('baseline_locality_dtype',k,d,n)
    for d,n,o in itertools.product(['f32','f64'],[64,65,1024,1025,65536,65537],[0,1]):add('alignment_tail','axpy',d,n,offset=o)
    for n,s in itertools.product([65536,4194304],[1,2,4,8]):add('stride','mul','f32',n,stride=s)
    for d,n in itertools.product(['f32','f64'],[1024,262144,16777216]):add('negative_strict_dot','dot',d,n)
    return list(cases.values())

def main():
    r=command([sys.executable,P/'scripts/build.py']);write_json(P/'evidence/build-invocation.json',r)
    if r['returncode']:raise RuntimeError(r)
    r=command(['clang','-O3','-mcpu=native',P/'src/peak.c','-o',P/'build/peak']);write_json(P/'evidence/peak-build.json',r)
    if r['returncode']:raise RuntimeError(r)
    dis=command(['xcrun','llvm-objdump','--disassemble',P/'build/peak'])
    (P/'evidence/peak-disassembly.txt').write_text(dis['stdout'])
    cases=make_plan();write_json(P/'config/plan.json',dict(created_utc=now(),trials=TRIALS,target_seconds=.03,seed=6320,cases=cases))
    write_json(P/'data/raw/environment-before.json',environment('project1'))
    rows=[]
    rawdir=P/'data/raw/runs';rawdir.mkdir(exist_ok=True)
    # Reproducible random order within each trial keeps builds interleaved.
    for trial in range(TRIALS):
        order=cases.copy();random.Random(6320+trial).shuffle(order)
        for idx,c in enumerate(order):
            path=rawdir/f'{c["id"]}-r{trial}.json'
            if path.exists():
                saved=json.loads(path.read_text())
                if saved['returncode']==0 and 'measurement' in saved:
                    rows.append(saved['measurement']);continue
            args=[P/f'build/{c["build"]}',c['kernel'],c['dtype'],str(c['n']),str(c['stride']),str(c['offset']),'.03']
            r=command(args,timeout=90)
            if r['returncode']==0:
                m=json.loads(r['stdout']);m.update(case_id=c['id'],trial=trial,suites=';'.join(c['suites']),started_utc=r['started_utc'])
                r['measurement']=m;rows.append(m)
            write_json(path,r)
            if r['returncode']:raise RuntimeError(f'Case failed: {path}')
            if idx%40==0:print(f'Project 1 trial {trial+1}/{TRIALS}: {idx+1}/{len(cases)}',flush=True)
    for kind,args in [('stream',[ROOT/'project1/.tools/bin/stream']),('peak',[P/'build/peak','50000000','0.5','0.0002'])]:
        for trial in range(TRIALS):
            r=command(args,timeout=60);write_json(P/f'data/raw/{kind}-{trial}.json',r)
            if r['returncode']:raise RuntimeError(r)
    import pandas as pd
    pd.DataFrame(rows).to_csv(P/'data/processed/measurements.csv',index=False)
    write_json(P/'data/raw/environment-after.json',environment('project1'))
    print(f'Project 1 complete: {len(rows)} measurements.',flush=True)
if __name__=='__main__':main()
