"""Bounded regular-file SSD experiments. Never accepts an arbitrary device path."""
from pathlib import Path
import itertools,json,math,os,random,shutil,stat,sys,time,uuid
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import command,write_json,environment,now,health
P=ROOT/'project3';WORK=P/'work';DATA=WORK/'ssd-test.bin';FIO=ROOT/'project3/.tools/bin/fio'
GIB=1024**3;TRIALS=3;WRITE_BUDGET=104*GIB

def own_workspace():
    WORK.mkdir(exist_ok=True);marker=WORK/'ownership.json'
    if not marker.exists():
        if DATA.exists() or (WORK/'verify.bin').exists():raise RuntimeError('Unowned test file; refusing to overwrite.')
        write_json(marker,dict(created_utc=now(),owner='ECSE6320 project3 disposable benchmark',token=str(uuid.uuid4())))
    for f in [DATA,WORK/'verify.bin']:
        if f.exists() and (f.is_symlink() or not stat.S_ISREG(f.lstat().st_mode)):raise RuntimeError('Only regular project-owned files allowed.')
    if shutil.disk_usage(WORK).free<8*GIB:raise RuntimeError('Less than 8GiB free; no SSD test started.')

def base_options(file=DATA,size=GIB):
    return dict(filename=str(file),size=str(size),ioengine='posixaio',direct='1',
                invalidate='0',allow_file_create='0',thread='1',numjobs='1',
                iodepth='1',mem_align='16384',randrepeat='1',randseed='6320',
                refill_buffers='1',buffer_compress_percentage='0',
                clat_percentiles='1',lat_percentiles='1',percentile_list='50:95:99:99.9',
                group_reporting='1',clocksource='clock_gettime')

def ensure_budget(reserve):
    entries=list((P/'data/raw/ledger').glob('*.json'))
    used=0
    for path in entries:
        d=json.loads(path.read_text());used+=d.get('actual_write_bytes',d['reserved_write_bytes'])
    if used+reserve>WRITE_BUDGET:raise RuntimeError(f'Write budget would be exceeded: {used}+{reserve}>{WRITE_BUDGET}')
    return used

def run_fio(case,trial,extra=None,file=DATA,size=None,prep=False):
    cid=case['id'];stem=f'{cid}-r{trial}';raw=P/'data/raw/runs'/f'{stem}.json';meta=P/'data/raw/runs'/f'{stem}-meta.json'
    if raw.exists() and meta.exists():
        d=json.loads(raw.read_text());m=json.loads(meta.read_text())
        if m.get('returncode')==0 and all(j.get('error',1)==0 for j in d.get('jobs',[])):return d
    opts=base_options(file,size or case.get('size',GIB))
    opts.update(rw=case['rw'],bs=str(case['bs']),iodepth=str(case.get('qd',1)),
                io_size=str(case.get('io_bytes',4*GIB)),runtime=str(case.get('runtime','1s')))
    if case.get('readpct') is not None:opts['rwmixread']=str(case['readpct'])
    if case.get('direct') is not None:opts['direct']=str(case['direct'])
    if extra:opts.update(extra)
    write_cap=int(opts['io_size']) if case['rw'] not in ['read','randread'] else 0
    ensure_budget(write_cap)
    ledger=P/'data/raw/ledger'/f'{stem}.json'
    write_json(ledger,dict(case_id=cid,trial=trial,reserved_write_bytes=write_cap,started_utc=now()))
    cfg=P/'config/generated'/f'{stem}.fio';cfg.parent.mkdir(exist_ok=True,parents=True)
    cfg.write_text('[global]\n'+'\n'.join(f'{k}={v}' for k,v in opts.items())+f'\n\n[{cid}]\n')
    # Parsing first prevents an invalid configuration from starting any workload.
    parse=command([FIO,'--parse-only',cfg],timeout=15)
    if parse['returncode']:
        write_json(meta,parse);raise RuntimeError(f'FIO configuration rejected: {cfg}: {parse["stderr"]}')
    before=health();r=command([FIO,cfg,'--output-format=json+','--output='+str(raw)],timeout=90)
    r.update(case=case,trial=trial,health_before=before,health_after=health(),disposable_regular_file=str(file),prep=prep)
    write_json(meta,r)
    if r['returncode'] or not raw.exists():raise RuntimeError(f'FIO failed: {meta}')
    d=json.loads(raw.read_text())
    if not d.get('jobs') or any(j.get('error',1) for j in d['jobs']):raise RuntimeError(f'FIO reported I/O error: {raw}')
    written=sum(j['write']['io_bytes'] for j in d['jobs'])
    if written>write_cap:raise RuntimeError('FIO exceeded its per-run I/O byte cap.')
    entry=json.loads(ledger.read_text());entry.update(actual_write_bytes=written,completed_utc=now());write_json(ledger,entry)
    return d

def make_plan():
    cases={}
    def add(suite,**kw):
        rw=kw['rw'];bs=kw['bs'];qd=kw.get('qd',1);size=kw.get('size',GIB);direct=kw.get('direct',1);pct=kw.get('readpct',100 if rw in ['read','randread'] else 0)
        cid=f'{rw}-b{bs}-q{qd}-range{size}-direct{direct}-r{pct}'
        if cid not in cases:
            cases[cid]=dict(id=cid,runtime='1s',io_bytes=2*GIB if rw not in ['read','randread'] else 4*GIB,**kw,suites=[])
        cases[cid]['suites'].append(suite)
    for bs,rw in itertools.product([4096,16384,32768,65536,131072,262144],['read','write','randread','randwrite']):
        add('block_pattern',rw=rw,bs=bs,qd=1)
        if (bs==4096 and rw in ['randread','randwrite']) or (bs==131072 and rw in ['read','write']):add('zero_queue',rw=rw,bs=bs,qd=1)
    for pct in [70,50]:add('rw_mix',rw='randrw',bs=4096,qd=16,readpct=pct)
    # Pure read/write endpoints for mix sweep use the same depth.
    add('rw_mix',rw='randread',bs=4096,qd=16)
    add('rw_mix',rw='randwrite',bs=4096,qd=16)
    for qd in [1,2,4,8,16,32,64,128,256]:add('queue_depth',rw='randread',bs=4096,qd=qd)
    for rw in ['read','write']:add('large_block_peak',rw=rw,bs=262144,qd=16)
    for size in [64*1024**2,256*1024**2,GIB]:add('working_range',rw='randread',bs=4096,qd=16,size=size)
    for direct in [0,1]:add('pitfall_buffered',rw='randread',bs=4096,qd=1,size=64*1024**2,direct=direct)
    return list(cases.values())

def main():
    own_workspace()
    for f in ['runs','ledger']:(P/'data/raw'/f).mkdir(exist_ok=True)
    cases=make_plan()
    # Upper bound includes all pure-write/mixed trials plus one-time initialization and validation.
    cap=sum(c['io_bytes']*TRIALS for c in cases if c['rw'] not in ['read','randread'])+GIB+64*1024**2
    if cap>WRITE_BUDGET:raise RuntimeError(f'Planned worst-case writes {cap} exceed {WRITE_BUDGET}')
    write_json(P/'config/plan.json',dict(created_utc=now(),trials=TRIALS,file_bytes=GIB,write_budget_bytes=WRITE_BUDGET,
               worst_case_write_bytes=cap,seed=6320,device_state='bounded current-state/burst tests; no forced SLC exhaustion',cases=cases))
    write_json(P/'data/raw/environment-before.json',environment('project3'))
    # Direct write/read CRC validation on a separate 64MiB disposable file.
    verify=dict(id='direct-crc32c-verify',rw='write',bs=65536,qd=8,io_bytes=64*1024**2,runtime='20s')
    run_fio(verify,0,extra=dict(allow_file_create='1',verify='crc32c',do_verify='1',verify_fatal='1',verify_state_save='0',end_fsync='1'),file=WORK/'verify.bin',size=64*1024**2,prep=True)
    init=dict(id='initialize-incompressible-file',rw='write',bs=1048576,qd=8,io_bytes=GIB,runtime='30s')
    run_fio(init,0,extra=dict(allow_file_create='1',end_fsync='1'),prep=True)
    if DATA.stat().st_size!=GIB:raise RuntimeError('Test file size differs from plan.')
    for trial in range(TRIALS):
        order=cases.copy();random.Random(26320+trial).shuffle(order)
        for idx,c in enumerate(order):
            # Warm the exact small buffered-read region before each intentional pitfall run.
            if c.get('direct')==0:
                fd=os.open(DATA,os.O_RDONLY)
                try:
                    offset=0
                    while offset<c['size']:
                        b=os.pread(fd,min(1024**2,c['size']-offset),offset)
                        if not b:raise RuntimeError('Short warmup read')
                        offset+=len(b)
                finally:os.close(fd)
            run_fio(c,trial)
            print(f'Project 3 trial {trial+1}/{TRIALS}: {idx+1}/{len(cases)} {c["id"]}',flush=True)
    # Select a measured read knee, then collect longer mid-depth / near-knee tails.
    import pandas as pd
    sys.path.insert(0,str(P/'scripts'))
    from analyze import load_rows
    rows=load_rows();df=pd.DataFrame(rows)
    curve=df[df.suites.str.contains('queue_depth')].groupby('requested_qd').iops.median().sort_index()
    maxrate=curve.max();near=int(curve[curve>=.9*maxrate].index[0]);mid=max(1,near//2)
    available=list(map(int,curve.index));mid=min(available,key=lambda q:abs(q-mid))
    tail=[]
    for role,qd in [('mid',mid),('near_knee',near)]:
        rate=max(1,float(curve.loc[qd]));duration=max(3,min(12,math.ceil(120000/rate)))
        c=dict(id=f'tail-{role}-q{qd}',rw='randread',bs=4096,qd=qd,io_bytes=64*GIB,runtime=f'{duration}s',suites=['tail_latency'],role=role,target_completions=120000)
        tail.append(c)
        for trial in range(TRIALS):run_fio(c,trial)
    write_json(P/'config/tail-plan.json',dict(selection_rule='smallest tested QD reaching 90% of maximum median IOPS',near_knee_qd=near,mid_qd=mid,cases=tail))
    write_json(P/'data/raw/environment-after.json',environment('project3'))
    print('Project 3 complete. Measured FIO writes:',ensure_budget(0),'bytes',flush=True)
if __name__=='__main__':main()
