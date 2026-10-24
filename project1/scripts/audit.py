"""Audit planned coverage, raw correctness, derived data, PMU exports and integrity."""
from pathlib import Path
import csv,gzip,hashlib,json,math,sys,tarfile,subprocess
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import now,write_json
checks=[]
def test(name,condition,detail=''):
    checks.append(dict(check=name,passed=bool(condition),detail=detail))
def load(p):return json.loads((ROOT/p).read_text())
def rows(p):
    with (ROOT/p).open() as f:return list(csv.DictReader(f))
def finite(v):
    try:return math.isfinite(float(v)) and float(v)>0
    except (TypeError,ValueError):return False

def main():
    for n,expected in [(1,1200),(2,355)]:
        pref=f'project{n}';plan=load(f'{pref}/config/plan.json');actual=set();raw=[]
        for p in (ROOT/pref/'data/raw/runs').glob('*.json'):
            d=json.loads(p.read_text());m=d.get('measurement',{})
            actual.add((m.get('case_id'),m.get('trial')));raw.append(m)
            test(str(p.relative_to(ROOT)),d.get('returncode')==0 and m.get('correctness') is True and finite(m.get('elapsed_ns')),'reference, exit status, finite timed interval')
        want={(c['id'],t) for c in plan['cases'] for t in range(plan['trials'])}
        test(f'{pref}: complete planned coverage',actual==want and len(raw)==expected,f'{len(raw)} records, {len(want)} planned; missing={list(want-actual)[:4]}')
        derived=rows(f'{pref}/data/processed/measurements.csv')
        test(f'{pref}: derived key coverage',{(r['case_id'],int(r['trial'])) for r in derived}==want and len(derived)==expected)
        for suffix in ['before','after','final']:
            test(f'{pref}: environment-{suffix}',(ROOT/pref/f'data/raw/environment-{suffix}.json').is_file())
    # Check units/formulas against original numeric records, not only row counts.
    p1=rows('project1/data/processed/measurements.csv')
    test('P1: cycles/element formula',all(math.isclose(float(r['cycles_per_element']),float(r['cycles'])/(float(r['iterations'])*float(r['elements_per_iteration'])),rel_tol=2e-7) for r in p1))
    test('P1: finite useful throughput',all(finite(r['gflops']) and finite(r['gib_per_s']) for r in p1))
    p2=rows('project2/data/processed/measurements.csv')
    test('P2: chase latency formula',all(math.isclose(float(r['latency_ns']),float(r['elapsed_ns'])/float(r['loads']),rel_tol=2e-7) for r in p2 if r['mode']=='chase'))
    test('P2: useful traffic/probe formulas',all(math.isclose(float(r['useful_gib_per_s']),float(r['traffic_ops'])*8/float(r['elapsed_ns'])*1e9/2**30,rel_tol=2e-7) and math.isclose(float(r['probe_latency_ns']),float(r['elapsed_ns'])/float(r['probe_loads']),rel_tol=2e-7) and int(float(r['traffic_ops']))==int(float(r['traffic_reads']))+int(float(r['traffic_writes'])) for r in p2 if r['mode']=='traffic'))
    provenance=load('project2/evidence/followup-source-provenance.json')
    test('P2: preserved follow-up source hash',hashlib.sha256((ROOT/'project2/evidence/collected-source/memory_variants.c').read_bytes()).hexdigest()==provenance['sha256'])
    for n in [1,2]:
        for entry in load(f'project{n}/evidence/layout-change.json')['changes']:
            old=ROOT/f'project{n}/evidence/collected-source'/Path(entry['file']).name
            new=ROOT/entry['file']
            test(entry['file']+': include-path-only relocation',hashlib.sha256(old.read_bytes()).hexdigest()==entry['original_sha256'] and old.read_text().replace('../../shared/measurement.h','measurement.h')==new.read_text())
    # Required P1 coverage plus independent boundary and negative controls.
    p=load('project1/config/plan.json');cs=p['cases']
    test('P1: three kernels, types, builds',{c['kernel'] for c in cs}>={'axpy','mul','stencil'} and {c['dtype'] for c in cs}=={'f32','f64'} and {c['build'] for c in cs}=={'scalar','auto','native'})
    test('P1: stride and misalignment coverage',{c['stride'] for c in cs}>={1,2,4,8} and {c['offset'] for c in cs}=={0,1})
    b=load('project1/evidence/correctness-boundaries.json');test('P1: 324 boundary checks',b['count']==324 and all(c['measurement']['correctness'] for c in b['checks']))
    v=load('project1/evidence/vectorization-summary.json');test('P1: SIMD verified, scalar disabled',not v[0]['vector_f32_instructions'] and all(x['vector_f32_instructions'] and x['vector_f64_instructions'] for x in v[1:]))
    peak=load('project1/evidence/peak-loop-verification.json');test('P1: accepted compute loop',peak['accepted'] and peak['vector_fma_instructions']==16)
    for kind in ['peak','stream']:
        test('P1: five '+kind+' references',all(load(f'project1/data/raw/{kind}-{t}.json')['returncode']==0 for t in range(5)))
    neg=list((ROOT/'project1/data/raw/negative').glob('*.json'))
    test('P1: 30 negative controls',len(neg)==30 and all((d:=json.loads(f.read_text()))['returncode']==0 and json.loads(d['stdout'])['correctness'] for f in neg))
    test('P1: negative control no vectors',all(not x['vector_arithmetic_in_control'] for x in load('project1/evidence/negative-verification.json').values()))
    # P2 mix, self-tests, page probe, supplementary timing and authentic PMU archives.
    p=load('project2/config/plan.json');cs=p['cases'];traffic=[c for c in cs if c['mode']=='traffic']
    test('P2: required pattern/granularity/mixes',all(any(c['spacing']==s and c['pattern']==q and c['readpct']==r for c in traffic) for s in [64,256,1024] for q in ['sequential','random'] for r in [0,50,70,100]))
    test('P2: reference tests',all(json.loads(load('project2/evidence/selftest.json')['stdout']).values()))
    h=json.loads(load('project2/evidence/hugepage.json')['stdout']);test('P2: explicit page-support record','allocation_succeeded' in h and h['native_page_bytes']==16384)
    follow=list((ROOT/'project2/data/raw/followup').glob('*.json'));test('P2: 33 follow-up timings',len(follow)==33 and all((d:=json.loads(f.read_text()))['returncode']==0 and json.loads(d['stdout'])['correctness'] for f in follow))
    plans=load('project2/config/counter-plan.json')['cases']+load('project2/config/followup-plan.json')['cases'];want={(c['id'],t) for c in plans for t in range(3)};got=set()
    events={'L1D_CACHE_MISS_LD_NONSPEC','L1D_TLB_MISS_NONSPEC','L2_TLB_MISS_DATA','Cycles','Instructions','INST_SIMD_ALU'}
    for f in (ROOT/'project2/data/raw/counters').glob('*.json'):
        d=json.loads(f.read_text());got.add((d['case']['id'],d['trial']))
        test(f.stem+': PMU capture',d['status']=='success' and d['sample_count']>=100 and set(d['events'])>=events and d['record']['returncode']==0 and all(e['returncode']==0 for e in d['exports']))
        companions=[f.with_name(f.stem+s) for s in ['-toc.xml.gz','-samples.xml.gz','.trace.tar.gz','-target.stdout']]
        test(f.stem+': complete original trace and exports',all(p.exists() and p.stat().st_size>0 for p in companions))
        # Validate gzip CRC on the small XML exports; tar members validate archive framing.
        for p in companions[:2]:
            with gzip.open(p,'rb') as stream:content=stream.read()
            test(p.name+': readable XML',b'<?xml' in content[:100])
        with tarfile.open(companions[2]) as archive:test(companions[2].name+': trace archive',any(m.name.startswith('recording.trace/') for m in archive.getmembers()))
    test('P2: 42 planned PMU captures',got==want and len(got)==42)
    test('P2: derived PMU count',len(rows('project2/data/processed/counters.csv'))==42 and len(load('project2/data/processed/counter-summary.json'))==42)
    # P3 every raw job, its configuration/ledger, percentiles, totals, budget and tails.
    plans=sum((load(f'project3/config/{name}.json')['cases'] for name in ['plan','tail-plan','parallelism-plan']),[])
    want={(c['id'],t) for c in plans for t in range(3)};got=set();preps=0;writes=0
    for meta in (ROOT/'project3/data/raw/runs').glob('*-meta.json'):
        m=json.loads(meta.read_text());stem=meta.name.removesuffix('-meta.json');d=json.loads(meta.with_name(stem+'.json').read_text())
        test(stem+': FIO success',m['returncode']==0 and bool(d['jobs']) and all(j['error']==0 for j in d['jobs']))
        cfg=ROOT/'project3/config/generated'/f'{stem}.fio';ledger=load(f'project3/data/raw/ledger/{stem}.json');payload=sum(j['write']['io_bytes'] for j in d['jobs']);writes+=payload
        test(stem+': config and ledger',cfg.exists() and ledger['actual_write_bytes']==payload and payload<=ledger['reserved_write_bytes'])
        path=Path(m['disposable_regular_file']);test(stem+': owned file scope',path.name in ['verify.bin','ssd-test.bin'] and path.parent.name=='work' and path.parent.parent.name=='project3')
        if m.get('prep'):preps+=1;continue
        c=m['case'];got.add((c['id'],m['trial']))
        for j in d['jobs']:
            for direction in ['read','write']:
                r=j[direction]
                if not r['total_ios']:continue
                pct=r['lat_ns']['percentile'];v=[next(value for key,value in pct.items() if abs(float(key)-p)<1e-7) for p in [50,95,99,99.9]]
                test(stem+': '+direction+' total-latency percentiles',all(finite(x) for x in v) and v==sorted(v))
                if 'tail_latency' in c['suites']:test(stem+': adequate tail sample',r['total_ios']>=100000)
        test(stem+': temperature recorded','temperature' in m['health_before'] and 'temperature' in m['health_after'])
    test('P3: all 141 planned performance runs',got==want and len(got)==141,f'missing={list(want-got)[:4]}')
    test('P3: two preparation jobs',preps==2)
    test('P3: write budget',writes==load('project3/data/processed/analysis.json')['total_test_write_bytes'] and writes<load('project3/config/plan.json')['write_budget_bytes'],str(writes)+' bytes')
    df=rows('project3/data/processed/measurements.csv');test('P3: derived rows and keys',len(df)==147 and {(r['case_id'],int(r['trial'])) for r in df}==want)
    test('P3: Little Law formula',all(math.isclose(float(r['estimated_mean_outstanding']),float(r['iops'])*float(r['combined_mean_latency_ns'])*1e-9,rel_tol=1e-9) for r in df))
    test('P3: percentiles have total-latency semantics',all(r['latency_percentile_kind']=='lat_ns' for r in df))
    test('P3: six tail records',len(rows('project3/data/processed/tail_counts.csv'))==6)
    test('P3: block-size and access matrix',all(any(c['bs']==b and c['rw']==r and 'block_pattern' in c['suites'] for c in plans) for b in [4096,16384,32768,65536,131072,262144] for r in ['read','write','randread','randwrite']))
    for suffix in ['before','after','final']:test('P3: environment-'+suffix,(ROOT/f'project3/data/raw/environment-{suffix}.json').exists())
    for name in ['README.md','AI_USE.md','REPORT.pdf','REPORT.md']:
        test('Unified document: '+name,(ROOT/name).exists())
    required_figures={
        1:['baseline_speedup','baseline_throughput','cycles_per_element','alignment_tail','stride','data_type','roofline','report_summary'],
        2:['working_set_latency','granularity_latency','pattern_rw_granularity','throughput_latency','page_locality','cache_reuse_pitfall','hardware_counters','numeric_cache_correlation','page_offset_control','tiny_cycle_unroll','report_summary'],
        3:['zero_queue','block_size_pattern','read_write_mix','throughput_latency','tail_latency','tail_histogram','range_and_cache_pitfall','report_summary'],
    }
    for n,names in required_figures.items():
        for name in names:
            test(f'P{n}: required figure {name}',(ROOT/f'project{n}/figures/{name}.png').is_file())
    for n in [1,2,3]:
        for f in (ROOT/f'project{n}/figures').glob('*.png'):
            test(str(f.relative_to(ROOT))+': PNG',f.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n')
    manifest=[]
    for n in [1,2,3]:
        paths=[p for p in (ROOT/f'project{n}').rglob('*') if p.is_file() and not any(v in p.parts for v in ['.tools','build','work','__pycache__','.cache']) and p.name not in ['SHA256SUMS','audit.json','.DS_Store']]
        if n==1:paths += [ROOT/f for f in ['README.md','AI_USE.md','REPORT.pdf','REPORT.md','.gitignore']]
        hashes=[]
        for p in sorted(paths):
            with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
            hashes.append(f'{digest}  {p.relative_to(ROOT)}')
        (ROOT/f'project{n}/evidence').mkdir(exist_ok=True)
        (ROOT/f'project{n}/evidence/SHA256SUMS').write_text('\n'.join(hashes)+'\n')
        manifest.extend(hashes)
    failed=[c for c in checks if not c['passed']]
    remote=subprocess.run(['git','remote','get-url','origin'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
    result=dict(captured_utc=now(),passed=not failed,checks=len(checks),failed=failed,integrity_files=len(manifest),project1_primary=1200,project1_extra_negative=30,project1_boundary_checks=324,project2_primary=355,project2_extra_timing=33,project2_PMU_captures=42,project3_performance_runs=141,project3_direction_rows=147,project3_payload_write_bytes=writes,external_submission=('Repository: '+remote) if remote else 'No Git remote configured.')
    write_json(ROOT/'project1/evidence/audit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='details'},indent=2))
    if failed:sys.exit(1)
if __name__=='__main__':main()
