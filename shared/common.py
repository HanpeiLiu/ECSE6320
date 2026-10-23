"""Shared provenance, subprocess capture, statistics, and figure conventions."""
from pathlib import Path
import datetime, hashlib, json, os, platform, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def write_json(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def command(args,timeout=120,cwd=ROOT):
    started=now(); t=time.monotonic()
    try:
        r=subprocess.run([str(x) for x in args],cwd=cwd,capture_output=True,text=True,timeout=timeout)
        return dict(command=[str(x) for x in args],started_utc=started,
                    elapsed_wall_s=time.monotonic()-t,returncode=r.returncode,
                    stdout=r.stdout,stderr=r.stderr)
    except subprocess.TimeoutExpired as e:
        return dict(command=[str(x) for x in args],started_utc=started,
                    elapsed_wall_s=time.monotonic()-t,returncode=124,
                    stdout=(e.stdout or b'').decode(errors='replace') if isinstance(e.stdout,bytes) else e.stdout or '',
                    stderr='TIMEOUT')

def power_state():
    return command(['/usr/bin/pmset','-g','batt'],timeout=10)['stdout'].strip()

def health():
    r=command([ROOT/'tools/bin/smartctl','-H','-A','-j','/dev/disk0'],timeout=20)
    try:
        d=json.loads(r['stdout'])
        return {k:d[k] for k in ['smart_status','temperature','nvme_smart_health_information_log'] if k in d}
    except (ValueError,KeyError):
        return {'unavailable':r['stderr']}

def environment(project):
    keys=['hw.memsize','hw.physicalcpu','hw.logicalcpu','hw.cachelinesize',
          'hw.pagesize','hw.optional.neon','hw.perflevel0.name',
          'hw.perflevel0.l1dcachesize','hw.perflevel0.l2cachesize',
          'hw.perflevel0.cpusperl2','hw.perflevel1.name',
          'hw.perflevel1.l1dcachesize','hw.perflevel1.l2cachesize']
    probes={name:command(args,timeout=30) for name,args in {
        'os':['sw_vers'],'kernel':['uname','-a'],
        'hardware':['system_profiler','SPHardwareDataType','-detailLevel','mini'],
        'compiler':['clang','--version'],'hardware_parameters':['/usr/sbin/sysctl',*keys],
        'power_policy':['pmset','-g','custom'],'battery':['pmset','-g','batt'],
        'disk_activity':['/usr/sbin/iostat','-d','-c','1'],
        'vm':['vm_stat'],'disk_space':['df','-h',str(ROOT)],
        'xcode':['xcodebuild','-version'],
        'pip':[sys.executable,'-m','pip','freeze'],
        'fio':[ROOT/'tools/bin/fio','--version'],
    }.items()}
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ['shared',project+'/src',project+'/scripts',project+'/config']
            for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    return dict(captured_utc=now(),platform=platform.platform(),python=sys.version,
                probes=probes,source_sha256=hashes,
                isolation='No strict CPU pinning or core isolation; user-initiated QoS is a scheduler hint only.',
                frequency='macOS dynamic frequency; no fixed-frequency/governor control claimed.',
                SMT='12 physical / 12 logical CPUs; no additional SMT threads.',
                NUMA='Single-socket unified-memory Mac; no user-controlled NUMA placement.',
                health=health())

def plotting():
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'figure.dpi':130,'savefig.dpi':180,'font.size':10,
                         'axes.grid':True,'grid.alpha':.25,'figure.constrained_layout.use':True})
    return plt

def source_notice(project):
    return f'''# AI-use and validation note\n\nOpenAI Codex generated and revised benchmark code, automation, plots, and this report.\nThe agent ran reference/sanity checks and inspected real compiler output and measurement records.\nNo result was invented to replace an unavailable hardware facility.\nThe student has not yet independently reviewed these artifacts; that review and explanation remain required before submission.\nInstallation checks and pilot runs are distinguished from final experiments.\nSee `{project}/data/raw/` for exact commands, raw outputs, failures, and environment records.\n'''

def markdown_table(frame):
    import math
    def cell(v):
        if isinstance(v,float):return f'{v:.5g}' if math.isfinite(v) else 'N/A'
        return str(v).replace('|','/').replace('\n',' ')
    cols=list(frame.columns)
    return '\n'.join(['| '+' | '.join(map(str,cols))+' |',
                      '| '+' | '.join(['---']*len(cols))+' |',
                      *['| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)]])
