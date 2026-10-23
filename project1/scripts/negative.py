"""Supplementary no-vectorization control; ordinary strict dot partially vectorized."""
from pathlib import Path
import itertools,json,random,re,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'shared'))
from common import command,write_json,now
P=ROOT/'project1';builds={'scalar':['-fno-vectorize','-fno-slp-vectorize'],'auto':[],'native':['-mcpu=native']}
records=[];verification={}
for name,flags in builds.items():
    r=command(['clang','-O3','-ffp-contract=off','-g',*flags,f'-DBUILD_NAME="{name}"','-Rpass=loop-vectorize','-Rpass-missed=loop-vectorize','-Rpass-analysis=loop-vectorize',P/'src/negative_dot.c','-o',P/f'build/negative-{name}']);records.append(r)
    if r['returncode']:raise RuntimeError(r)
    (P/f'evidence/negative-{name}-vectorization.txt').write_text(r['stderr'])
    dis=command(['xcrun','llvm-objdump','--disassemble',P/f'build/negative-{name}'])['stdout']
    (P/f'evidence/negative-{name}-disassembly.txt').write_text(dis)
    body=dis.split('<_observable_dot>:',1)[1].split('\n\n',1)[0]
    verification[name]={'vector_arithmetic_in_control':bool(re.search(r'\b(?:fmul|fadd|fmla)\.(?:4s|2d)\b',body)),'excerpt':body}
    if verification[name]['vector_arithmetic_in_control']:raise RuntimeError('Negative control unexpectedly vectorized')
write_json(P/'evidence/negative-build.json',records);write_json(P/'evidence/negative-verification.json',verification)
write_json(P/'config/negative-plan.json',dict(created_utc=now(),reason='Ordinary strict dot uses SIMD products followed by ordered scalar additions; add volatile accumulator control to explicitly test a non-vectorized loop.',sizes=[1024,1048576],trials=5,builds=list(builds)))
rows=[]
for trial in range(5):
    order=list(itertools.product(builds,[1024,1048576]));random.Random(46320+trial).shuffle(order)
    for name,n in order:
        r=command([P/f'build/negative-{name}',str(n)]);write_json(P/f'data/raw/negative/{name}-n{n}-r{trial}.json',r)
        if r['returncode']:raise RuntimeError(r)
        m=json.loads(r['stdout']);m['trial']=trial;rows.append(m)
import pandas as pd
pd.DataFrame(rows).to_csv(P/'data/processed/negative_control.csv',index=False)
print('30 negative controls passed; all three builds contain no vector arithmetic in observable_dot.')
