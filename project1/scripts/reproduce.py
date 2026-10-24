#!/usr/bin/env python3
"""Rebuild derived results, or recollect into a new directory with explicit SSD opt-in."""
from pathlib import Path
import argparse,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
def run(script,root):
    subprocess.run([sys.executable,str(root/script)],cwd=root,check=True)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collect-to',type=Path)
    p.add_argument('--allow-ssd-writes',action='store_true')
    a=p.parse_args();root=ROOT
    if a.collect_to:
        if not a.allow_ssd_writes:p.error('Add --allow-ssd-writes to enable the bounded dedicated-file workload')
        root=a.collect_to.expanduser().resolve()
        if root.exists():p.error('Destination must not exist')
        root.mkdir(parents=True)
        for n in [1,2,3]:
            shutil.copytree(ROOT/f'project{n}',root/f'project{n}',ignore=shutil.ignore_patterns('data','figures','build','work','.tools','.cache','__pycache__','audit.json','SHA256SUMS'))
            for d in ['build','figures','data/raw','data/processed']:(root/f'project{n}'/d).mkdir(parents=True,exist_ok=True)
            if (ROOT/f'project{n}/.tools').exists():(root/f'project{n}/.tools').symlink_to(ROOT/f'project{n}/.tools',target_is_directory=True)
        for f in ['README.md','AI_USE.md','REPORT.pdf','.gitignore']:shutil.copy2(ROOT/f,root/f)
        (root/'.venv').symlink_to(Path(sys.prefix),target_is_directory=True)
        for script in ['project1/scripts/run.py','project1/scripts/finalize_validation.py','project1/scripts/negative.py','project2/scripts/run.py','project3/scripts/run.py','project3/scripts/parallelism.py','project2/scripts/profile.py','project2/scripts/followup.py']:run(script,root)
        sys.path.insert(0,str(root/'project1/scripts'))
        from common import environment,write_json
        for n in [1,2,3]:write_json(root/f'project{n}/data/raw/environment-final.json',environment(f'project{n}'))
        # The report is regenerated separately: it must describe the new collection.
        (root/'REPORT.pdf').unlink()
        print('Recollection complete. Regenerate REPORT.pdf with scripts/report.py before submission.',flush=True)
    for n in [1,2,3]:run(f'project{n}/scripts/analyze.py',root)
    if (root/'REPORT.pdf').exists():run('project1/scripts/audit.py',root)
    print('Results:',root)
if __name__=='__main__':main()
