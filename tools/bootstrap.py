#!/usr/bin/env python3
"""Fetch pinned upstream sources (no installation outside this project)."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,urllib.request
P=Path(__file__).resolve().parent;SRC=P/'src';SRC.mkdir(exist_ok=True)
m=json.loads((P/'manifest.json').read_text())
folders={'fio':'fio-3.43','STREAM':'stream','lmbench':'lmbench'}
for t in m['tools']:
    if t['name'] in folders:
        dst=SRC/folders[t['name']]
        if dst.exists():
            commit=subprocess.check_output(['git','-C',str(dst),'rev-parse','HEAD'],text=True).strip()
            if commit!=t['commit']:raise RuntimeError(f'Unexpected checkout: {dst}')
            continue
        subprocess.run(['git','clone','--no-checkout',t['source'],str(dst)],check=True)
        subprocess.run(['git','-C',str(dst),'checkout','--detach',t['commit']],check=True)
    else:
        archive=SRC/'smartmontools-7.5.tar.gz';dst=SRC/'smartmontools-7.5'
        if not archive.exists():
            with urllib.request.urlopen(t['source'],timeout=120) as response:archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=t['sha256']:raise RuntimeError('smartmontools SHA256 mismatch')
        if not dst.exists():
            with tarfile.open(archive) as f:f.extractall(SRC,filter='data')
if '--build' in sys.argv:subprocess.run([sys.executable,str(P/'rebuild.py')],check=True)
else:print('Pinned sources ready. Rebuild with: python tools/rebuild.py')
