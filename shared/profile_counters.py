"""Reproducible Instruments manual-PMU capture and sampled kernel attribution."""
from pathlib import Path
import gzip,hashlib,json,shlex,shutil,sys,tarfile,tempfile,xml.etree.ElementTree as ET
from common import ROOT,command,write_json,now
TEMPLATE=ROOT/'project2/evidence/ECSE6320-Counters.tracetemplate'

def parse_counts(xml,executable,kernel):
    tree=ET.parse(xml).getroot();ids={x.get('id'):x for x in tree.iter() if x.get('id')}
    def resolve(x):return ids.get(x.get('ref'),x) if x is not None else None
    result=[]
    for row in tree.iter('row'):
        process=resolve(row.find('process'))
        if process is None or not process.get('fmt','').startswith(executable+' ('):continue
        bt=resolve(row.find('backtrace'));frames=[]
        if bt is not None:frames=[resolve(f).get('name','') for f in bt.findall('frame')]
        # Attribute only samples whose executing leaf is the selected kernel.
        if not frames or frames[0].lstrip('_')!=kernel:continue
        values=resolve(row.find('pmc-events'))
        if values is None:continue
        vals=[int(x) for x in (values.text or '').split()]
        if not vals:continue
        t=resolve(row.find('sample-time'));core=resolve(row.find('core'));weight=resolve(row.find('weight'))
        result.append(dict(time_ns=int(t.text),core=core.get('fmt','') if core is not None else '',
                           weight_ns=int(weight.text) if weight is not None else 0,values=vals,leaf=frames[0]))
    return result

def capture(case,trial,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    stem=f'{case["id"]}-r{trial}';meta=output/f'{stem}.json'
    if meta.exists():
        d=json.loads(meta.read_text())
        if d.get('status')=='success':return d
    with tempfile.TemporaryDirectory(prefix='ecse6320-pmu-',dir='/private/tmp') as td:
        temp=Path(td);exe=temp/'kernel';shutil.copy2(case['executable'],exe)
        trace=temp/'recording.trace';stdout=temp/'target.stdout'
        args=['xctrace','record','--template',TEMPLATE,'--time-limit','20s',
              '--output',trace,'--target-stdout',stdout,'--launch','--',exe,*case['args']]
        r=command(args,timeout=75)
        toc=temp/'toc.xml';data=temp/'counters.xml'
        exports=[]
        for extra in [['--toc','--output',toc],
                      ['--xpath','/trace-toc/run[@number="1"]/data/table[@schema="counters-profile"]','--output',data]]:
            e=command(['xctrace','export','--input',trace,*extra],timeout=60);exports.append(e)
            if e['returncode']:raise RuntimeError(e)
        root=ET.parse(toc).getroot()
        table=next(t for t in root.iter('table') if t.get('schema')=='counters-profile')
        events=shlex.split(table.get('pmc-events',''))
        samples=parse_counts(data,exe.name,case['kernel'])
        for path,dest in [(toc,output/f'{stem}-toc.xml.gz'),(data,output/f'{stem}-samples.xml.gz')]:
            with gzip.open(dest,'wb') as f:f.write(path.read_bytes())
        # Preserve the original trace, compressed, so counter interpretation is auditable.
        with tarfile.open(output/f'{stem}.trace.tar.gz','w:gz') as f:f.add(trace,arcname='recording.trace')
        target_stdout=stdout.read_text() if stdout.exists() else ''
        (output/f'{stem}-target.stdout').write_text(target_stdout)
        if r['returncode'] or len(samples)<100:
            write_json(meta,dict(status='failed',record=r,exports=exports,samples=len(samples),case=case))
            raise RuntimeError(f'Insufficient successful PMU samples: {meta}')
        totals={name:sum(s['values'][i] for s in samples) for i,name in enumerate(events)}
        result=dict(status='success',case=case,trial=trial,record=r,exports=exports,
                    events=events,sample_count=len(samples),sample_weight_ns=sum(s['weight_ns'] for s in samples),
                    event_sums=totals,p_core_sample_fraction=sum('P Core' in s['core'] for s in samples)/len(samples),
                    attribution='Sampled deltas attributed to leaf kernel; includes warm-up calls to that kernel, excludes allocation/initialization/driver samples. Not whole-process perf-stat totals.',
                    executable_sha256=hashlib.sha256(Path(case['executable']).read_bytes()).hexdigest(),
                    template_sha256=hashlib.sha256(TEMPLATE.read_bytes()).hexdigest())
        write_json(meta,result);return result
