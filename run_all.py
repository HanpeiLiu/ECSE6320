#!/usr/bin/env python3
"""Analyze saved results, or collect into a NEW directory with explicit SSD-write opt-in."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent

def run(script,root=ROOT):
    print(script,flush=True)
    subprocess.run([sys.executable,str(root/script)],cwd=root,check=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collect-to',type=Path,help='NEW directory for a separate data collection; original results are preserved')
    p.add_argument('--allow-ssd-writes',action='store_true',help='Enable the bounded regular-file SSD experiment (104GiB maximum test writes)')
    args=p.parse_args()
    if args.collect_to:
        if not args.allow_ssd_writes:p.error('Collection includes SSD writes; add --allow-ssd-writes to enable the documented file-only workload')
        dst=args.collect_to.expanduser().resolve()
        if dst.exists():p.error('Destination must not exist')
        dst.mkdir(parents=True)
        for name in ['shared','tools','project1','project2','project3']:
            shutil.copytree(ROOT/name,dst/name,ignore=shutil.ignore_patterns('data','figures','build','work','src' if name=='tools' else '__nothing__','bin','logs','__pycache__'))
        for name in ['requirements.txt','activate.zsh','README.md','DATA_DICTIONARY.md','COMPLETENESS.md','REQUIREMENTS.csv','run_all.py','.gitignore','ECSE4320_6320_Class-wide_Projects.pdf']:
            if (ROOT/name).exists():shutil.copy2(ROOT/name,dst/name)
        # Existing local tools are read-only dependencies; data and test files live in dst.
        (dst/'tools/bin').symlink_to(ROOT/'tools/bin',target_is_directory=True)
        (dst/'.venv').symlink_to(Path(sys.prefix),target_is_directory=True)
        for n in [1,2,3]:
            for d in ['build','figures','data/raw','data/processed']:(dst/f'project{n}'/d).mkdir(parents=True,exist_ok=True)
        for script in ['project1/scripts/run.py','project1/scripts/finalize_validation.py','project1/scripts/negative.py','project2/scripts/run.py','project3/scripts/run.py','project3/scripts/parallelism.py','project2/scripts/profile.py','project2/scripts/followup.py']:
            run(script,dst)
        sys.path.insert(0,str(dst/'shared'))
        from common import environment,write_json
        for n in [1,2,3]:write_json(dst/f'project{n}/data/raw/environment-final.json',environment(f'project{n}'))
        root=dst
    else:root=ROOT
    for n in [1,2,3]:run(f'project{n}/scripts/analyze.py',root)
    run('shared/audit.py',root)
    print('Results and audit:',root,flush=True)
if __name__=='__main__':main()
