"""Validate the corrected compute ceiling and boundary/access-pattern correctness."""
from pathlib import Path
import itertools,json,re,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import command,write_json
P=ROOT/'project1'
r=command(['clang','-O3','-mcpu=native',P/'src/peak.c','-o',P/'build/peak']);write_json(P/'evidence/peak-build.json',r)
if r['returncode']:raise RuntimeError(r)
r=command(['xcrun','llvm-objdump','--disassemble',P/'build/peak'])
(P/'evidence/peak-disassembly.txt').write_text(r['stdout'])
fmas=[line for line in r['stdout'].splitlines() if re.search(r'\bfmla\.4s\b',line)]
write_json(P/'evidence/peak-loop-verification.json',dict(vector_fma_instructions=len(fmas),expected=16,accepted=len(fmas)==16,excerpt=fmas))
if len(fmas)!=16:raise RuntimeError('Compute loop FLOP count not validated by disassembly')
for trial in range(5):
    r=command([P/'build/peak','50000000','0.5','0.0002']);write_json(P/f'data/raw/peak-{trial}.json',r)
    if r['returncode']:raise RuntimeError(r)
checks=[]
for build,kernel,dtype,n,stride,offset in itertools.product(['scalar','auto','native'],['axpy','mul','stencil'],['f32','f64'],[3,17,1025],[1,2,8],[0,1]):
    args=[P/f'build/{build}',kernel,dtype,str(n),str(stride),str(offset),'0.0001']
    r=command(args,timeout=15)
    if r['returncode']:raise RuntimeError(r)
    m=json.loads(r['stdout']);assert m['correctness'];checks.append(dict(command=r['command'],measurement=m))
write_json(P/'evidence/correctness-boundaries.json',dict(count=len(checks),all_passed=True,checks=checks))
print('Project 1: accepted 16-FMA compute ceiling; boundary checks passed:',len(checks),flush=True)
