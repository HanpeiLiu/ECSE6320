"""Fetch pinned upstream sources and build only STREAM, FIO and smartctl locally."""
from pathlib import Path
import hashlib,json,subprocess,tarfile,urllib.request
ROOT=Path(__file__).resolve().parents[2]
for n in [1,3]:
    project=ROOT/f'project{n}';local=project/'.tools';src=local/'src';binpath=local/'bin'
    src.mkdir(parents=True,exist_ok=True);binpath.mkdir(exist_ok=True)
    for t in json.loads((project/'config/tools.json').read_text())['tools']:
        name=t['name'];folder={'STREAM':'stream','fio':'fio-3.43','smartctl':'smartmontools-7.5'}[name];dst=src/folder
        if 'commit' in t:
            if not dst.exists():
                subprocess.run(['git','clone','--no-checkout',t['source'],str(dst)],check=True)
                subprocess.run(['git','-C',str(dst),'checkout','--detach',t['commit']],check=True)
            if subprocess.check_output(['git','-C',str(dst),'rev-parse','HEAD'],text=True).strip()!=t['commit']:raise RuntimeError('Unexpected source commit')
        else:
            archive=src/(folder+'.tar.gz')
            if not archive.exists():
                with urllib.request.urlopen(t['source'],timeout=120) as response:archive.write_bytes(response.read())
            if hashlib.sha256(archive.read_bytes()).hexdigest()!=t['sha256']:raise RuntimeError('Source archive SHA256 mismatch')
            if not dst.exists():
                with tarfile.open(archive) as f:f.extractall(src,filter='data')
        commands={'STREAM':[['clang','-O3','-mcpu=native','-DSTREAM_ARRAY_SIZE=10000000','-DNTIMES=10','stream.c','-o',str(binpath/'stream')]],
                  'fio':[['./configure','--prefix='+str(local)],['make','-j4']],
                  'smartctl':[['./configure','--prefix='+str(local),'--without-initscriptdir','--without-update-smart-drivedb'],['make','-j4','smartctl']]}[name]
        for cmd in commands:subprocess.run(cmd,cwd=dst,check=True)
        if name!='STREAM':
            import shutil
            shutil.copy2(dst/name,binpath/name)
print('Tools are installed inside project1/.tools and project3/.tools.')
