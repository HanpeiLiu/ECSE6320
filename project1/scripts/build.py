from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'shared'))
from common import command,write_json
P=ROOT/'project1';(P/'build').mkdir(exist_ok=True);(P/'evidence').mkdir(exist_ok=True)
base=['-O3','-ffp-contract=off','-g','-Wall','-Wextra']
records=[]
for name,extra in {'scalar':['-fno-vectorize','-fno-slp-vectorize'],'auto':[],'native':['-mcpu=native']}.items():
    flags=base+extra
    args=['clang',*flags,'-Rpass=loop-vectorize','-Rpass-missed=loop-vectorize','-Rpass-analysis=loop-vectorize','-c',P/'src/kernels.c','-o',P/f'build/{name}-kernels.o']
    r=command(args);records.append(r)
    (P/f'evidence/{name}-vectorization.txt').write_text(r['stderr'])
    if r['returncode']:raise RuntimeError(r)
    args=['clang',*flags,f'-DBUILD_NAME="{name}"','-c',P/'src/bench.c','-o',P/f'build/{name}-driver.o']
    r=command(args);records.append(r)
    if r['returncode']:raise RuntimeError(r)
    r=command(['clang',P/f'build/{name}-driver.o',P/f'build/{name}-kernels.o','-o',P/f'build/{name}']);records.append(r)
    if r['returncode']:raise RuntimeError(r)
    r=command(['xcrun','llvm-objdump','--disassemble',P/f'build/{name}-kernels.o'])
    (P/f'evidence/{name}-disassembly.txt').write_text(r['stdout'])
write_json(P/'evidence/build.json',records)
print('Project 1: scalar, auto, native built; compiler reports and disassembly saved.')
