from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import plotting,write_json,markdown_table
P=ROOT/'project3'

def load_rows():
    rows=[]
    for meta in sorted((P/'data/raw/runs').glob('*-meta.json')):
        m=json.loads(meta.read_text())
        if m.get('returncode') or m.get('prep') or 'case' not in m:continue
        c=m['case'];raw=meta.with_name(meta.name.replace('-meta.json','.json'))
        d=json.loads(raw.read_text())
        for job in d['jobs']:
            reads=job['read'];writes=job['write'];n=sum(v['total_ios'] for v in [reads,writes]);ios=reads['iops']+writes['iops']
            # FIO percentiles are per direction. Preserve separate read/write rows; totals remain explicit.
            for direction,v in [('read',reads),('write',writes)]:
                if not v['total_ios']:continue
                lat=v.get('lat_ns',{});clat=v.get('clat_ns',{});pct=lat.get('percentile',clat.get('percentile',{}))
                def perc(q):
                    for k,val in pct.items():
                        if abs(float(k)-q)<1e-6:return val
                    return None
                row=dict(case_id=c['id'],trial=m['trial'],suites=';'.join(c.get('suites',[])),rw=c['rw'],
                         bs=c['bs'],requested_qd=c.get('qd',1),numjobs=c.get('numjobs',1),range_bytes=c.get('size',1024**3),
                         direct=c.get('direct',1),read_percent=c.get('readpct',100 if c['rw'] in ['read','randread'] else 0),
                         direction=direction,io_count=v['total_ios'],total_io_count=n,iops=ios,direction_iops=v['iops'],
                         bandwidth_mib_s=(reads['bw_bytes']+writes['bw_bytes'])/1024**2,
                         mean_latency_ns=lat.get('mean'),mean_clat_ns=clat.get('mean'),
                         combined_mean_latency_ns=sum(j['lat_ns']['mean']*j['total_ios'] for j in [reads,writes])/max(n,1),
                         p50_ns=perc(50),p95_ns=perc(95),p99_ns=perc(99),p999_ns=perc(99.9),
                         latency_percentile_kind='lat_ns' if 'percentile' in lat else 'clat_ns',
                         runtime_ms=v['runtime'],job_runtime_ms=job.get('job_runtime'),
                         slat_mean_ns=v.get('slat_ns',{}).get('mean'),
                         cpu_user_pct=job.get('usr_cpu'),cpu_system_pct=job.get('sys_cpu'),
                         error=job['error'],actual_write_bytes=writes['io_bytes'],
                         estimated_mean_outstanding=ios*sum(j['lat_ns']['mean']*j['total_ios'] for j in [reads,writes])/max(n,1)*1e-9,
                         effective_depth_distribution=json.dumps(job.get('iodepth_level',{}),sort_keys=True),
                         temperature_before=m.get('health_before',{}).get('temperature',{}).get('current'),
                         temperature_after=m.get('health_after',{}).get('temperature',{}).get('current'),
                         p999_tail_expected_samples=v['total_ios']*.001,
                         max_latency_ns=lat.get('max'),raw_file=str(raw.relative_to(P)))
                rows.append(row)
    return rows

def main():
    import pandas as pd
    import numpy as np
    plt=plotting();rows=load_rows();df=pd.DataFrame(rows)
    df.to_csv(P/'data/processed/measurements.csv',index=False)
    unique=df.drop_duplicates(['case_id','trial'])
    metrics=['iops','bandwidth_mib_s','combined_mean_latency_ns','mean_latency_ns','p50_ns','p95_ns','p99_ns','p999_ns','estimated_mean_outstanding']
    summary=df.groupby(['case_id','rw','bs','requested_qd','numjobs','range_bytes','direct','read_percent','direction'])[metrics].agg(['median','std','min','max','count'])
    summary.columns=['_'.join(c) for c in summary.columns];summary.reset_index().to_csv(P/'data/processed/summary.csv',index=False)
    zero=df[df.suites.str.contains('zero_queue')]
    table=zero.groupby(['rw','bs'])[['mean_latency_ns','p50_ns','p95_ns','p99_ns','io_count']].median().reset_index()
    for col in ['mean_latency_ns','p50_ns','p95_ns','p99_ns']:table[col.replace('_ns','_us')]=table.pop(col)/1000
    table.to_csv(P/'data/processed/zero_queue_baselines.csv',index=False)
    fig,ax=plt.subplots(figsize=(9,4));labels=[f'{r.rw}\n{r.bs//1024}KiB' for r in table.itertuples()]
    for j,col in enumerate(['p50_us','p95_us','p99_us']):ax.bar(np.arange(len(table))+(j-1)*.25,table[col],width=.25,label=col.replace('_us',''))
    ax.set_xticks(range(len(labels)),labels);ax.set_ylabel('Total I/O latency (µs)');ax.set_title('QD=1; medians of 3 trials');ax.legend();fig.savefig(P/'figures/zero_queue.png');plt.close(fig)
    block=df[df.suites.str.contains('block_pattern')]
    fig,axs=plt.subplots(2,2,figsize=(11,8))
    for j,pattern in enumerate(['sequential','random']):
        for rw in (['read','write'] if pattern=='sequential' else ['randread','randwrite']):
            z=block[block.rw==rw]
            for i,(metric,label,scale) in enumerate([('bandwidth_mib_s','MiB/s',1),('mean_latency_ns','Total I/O mean latency (µs)',.001)]):
                q=z.groupby('bs')[metric].agg(['median','std']);axs[i,j].errorbar(q.index/1024,q['median']*scale,yerr=q['std']*scale,marker='o',capsize=3,label=rw)
                axs[i,j].set_xscale('log',base=2);axs[i,j].set_xlabel('Block size (KiB)');axs[i,j].set_ylabel(label);axs[i,j].set_title(pattern);axs[i,j].legend()
    fig.suptitle('QD=1 block/pattern matrix: throughput and latency from identical runs')
    fig.savefig(P/'figures/block_size_pattern.png');plt.close(fig)
    mix=unique[unique.suites.str.contains('rw_mix')]
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for ax,metric,label,scale in [(axs[0],'iops','Total IOPS',1),(axs[1],'combined_mean_latency_ns','Combined mean total latency (µs)',.001)]:
        q=mix.groupby('read_percent')[metric].agg(['median','std']);ax.errorbar(q.index,q['median']*scale,yerr=q['std']*scale,marker='o',capsize=4);ax.set_xticks([0,50,70,100]);ax.set_xlabel('Configured read percentage');ax.set_ylabel(label)
    fig.suptitle('Random 4KiB, requested QD=16, one process');fig.savefig(P/'figures/read_write_mix.png');plt.close(fig)
    curve=unique[unique.suites.str.contains('queue_depth')]
    q=curve.groupby('requested_qd')[['iops','combined_mean_latency_ns','estimated_mean_outstanding']].agg(['median','std'])
    knee=int(q.index[q[('iops','median')]>=.9*q[('iops','median')].max()][0])
    fig,axs=plt.subplots(1,2,figsize=(12,4.5))
    axs[0].errorbar(q[('combined_mean_latency_ns','median')]/1000,q[('iops','median')],xerr=q[('combined_mean_latency_ns','std')]/1000,yerr=q[('iops','std')],marker='o',capsize=3,label='1 process: QD sweep')
    for d in [1,2,4,8,16]:axs[0].annotate(f'QD{d}',(q.loc[d,('combined_mean_latency_ns','median')]/1000,q.loc[d,('iops','median')]),xytext=(3,-13 if d==16 else 4),textcoords='offset points',fontsize=8)
    axs[0].annotate('QD32–256 cluster',(q.loc[256,('combined_mean_latency_ns','median')]/1000,q.loc[256,('iops','median')]),xytext=(30,-45),textcoords='offset points',fontsize=8,arrowprops={'arrowstyle':'-','color':'gray'})
    par=unique[unique.suites.str.contains('parallelism')]
    pq=par.groupby('numjobs')[['iops','combined_mean_latency_ns','estimated_mean_outstanding']].agg(['median','std'])
    if len(pq):
        axs[0].errorbar(pq[('combined_mean_latency_ns','median')]/1000,pq[('iops','median')],xerr=pq[('combined_mean_latency_ns','std')]/1000,yerr=pq[('iops','std')],marker='s',capsize=3,label='QD8 per forked process')
        for jobs in pq.index:axs[0].annotate(f'{jobs} jobs',(pq.loc[jobs,('combined_mean_latency_ns','median')]/1000,pq.loc[jobs,('iops','median')]),xytext=(3,4),textcoords='offset points',fontsize=8)
    axs[0].set_xlabel('Combined mean total I/O latency (µs)');axs[0].set_ylabel('Total IOPS');axs[0].legend(fontsize=8)
    axs[1].errorbar(q.index,q[('estimated_mean_outstanding','median')],yerr=q[('estimated_mean_outstanding','std')],marker='o',label='λ × W (application lifetime)')
    axs[1].plot(q.index,q.index,ls='--',color='gray',label='Requested QD');axs[1].set_xscale('log',base=2);axs[1].set_yscale('log',base=2);axs[1].set_xlabel('Requested QD, single process');axs[1].set_ylabel('Mean outstanding request estimate');axs[1].legend(fontsize=8)
    fig.suptitle('Random 4KiB reads: throughput–latency and the effective-depth pitfall')
    fig.savefig(P/'figures/throughput_latency.png');plt.close(fig)
    q.columns=['_'.join(c) for c in q.columns];q.reset_index().to_csv(P/'data/processed/queue_curve.csv',index=False)
    if len(pq):
        pq.columns=['_'.join(c) for c in pq.columns];pq.reset_index().to_csv(P/'data/processed/parallelism.csv',index=False)
    tails=df[df.suites.str.contains('tail_latency')]
    fig,ax=plt.subplots(figsize=(10,5));names=list(tails.case_id.unique());positions=np.arange(4)
    for j,name in enumerate(names):
        z=tails[tails.case_id==name];med=z[['p50_ns','p95_ns','p99_ns','p999_ns']].median()/1000
        lo=z[['p50_ns','p95_ns','p99_ns','p999_ns']].min()/1000;hi=z[['p50_ns','p95_ns','p99_ns','p999_ns']].max()/1000
        x=positions+(j-(len(names)-1)/2)*.12;ax.errorbar(x,med,yerr=[med-lo,hi-med],marker='o',capsize=4,label=name)
        for _,r in z.iterrows():ax.scatter(x,[r.p50_ns/1000,r.p95_ns/1000,r.p99_ns/1000,r.p999_ns/1000],s=15,alpha=.5)
    ax.set_xticks(positions,['p50','p95','p99','p99.9']);ax.set_yscale('log');ax.set_ylabel('Total I/O latency (µs, log)');ax.set_title('Tail confirmation: all trials, median and min–max range');ax.legend(fontsize=8)
    fig.savefig(P/'figures/tail_latency.png');plt.close(fig)
    tails[['case_id','trial','io_count','p50_ns','p95_ns','p99_ns','p999_ns','p999_tail_expected_samples']].to_csv(P/'data/processed/tail_counts.csv',index=False)
    # Preserve and plot the actual completion-latency histogram, distinct from total latency.
    fig,ax=plt.subplots(figsize=(8,5))
    for name in names:
        hist={}
        for _,r in tails[tails.case_id==name].iterrows():
            raw=json.loads((P/r.raw_file).read_text())
            for job in raw['jobs']:
                for b,count in job['read'].get('clat_ns',{}).get('bins',{}).items():hist[int(b)]=hist.get(int(b),0)+count
        if hist:
            xs=np.array(sorted(hist));counts=np.array([hist[b] for b in xs]);survival=np.maximum(1-np.cumsum(counts)/counts.sum(),1/counts.sum())
            ax.loglog(xs/1000,survival,label=name)
    ax.set_xlabel('Completion latency (µs)');ax.set_ylabel('Fraction above latency');ax.set_title('Pooled raw completion-latency histogram tails');ax.legend(fontsize=8)
    fig.savefig(P/'figures/tail_histogram.png');plt.close(fig)
    ranges=unique[unique.suites.str.contains('working_range')]
    pit=unique[unique.suites.str.contains('pitfall_buffered')]
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    a=ranges.groupby('range_bytes').iops.agg(['median','std']);axs[0].bar([str(int(n/1024**2)) for n in a.index],a['median'],yerr=a['std'],capsize=4);axs[0].set_xlabel('Logical file range (MiB)');axs[0].set_ylabel('IOPS');axs[0].set_title('Random 4KiB, QD16, direct=1')
    b=pit.groupby('direct').iops.agg(['median','std']);axs[1].bar(['Buffered, warmed','F_NOCACHE'],b['median'],yerr=b['std'],capsize=4);axs[1].set_ylabel('IOPS');axs[1].set_title('64MiB range, random 4KiB, QD1')
    fig.savefig(P/'figures/range_and_cache_pitfall.png');plt.close(fig)
    temps=unique[['temperature_before','temperature_after']]
    ledger=[json.loads(f.read_text()) for f in (P/'data/raw/ledger').glob('*.json')]
    writes=sum(x.get('actual_write_bytes',x['reserved_write_bytes']) for x in ledger)
    stats=dict(direction_rows=len(df),measured_case_trials=len(unique),cases=unique.case_id.nunique(),
               io_errors=int(df.error.sum()),single_process_knee_qd=knee,
               maximum_observed_random_read_iops=float(unique[(unique.rw=='randread')&(unique.direct==1)].iops.max()),
               maximum_observed_sequential_mib_s=float(unique[unique.rw=='read'].bandwidth_mib_s.max()),
               total_test_write_bytes=writes,total_test_write_GiB=writes/1024**3,
               minimum_tail_io_count=int(tails.io_count.min()),minimum_p999_tail_expected_samples=float(tails.p999_tail_expected_samples.min()),
               temperature_min_C=float(temps.min().min()),temperature_max_C=float(temps.max().max()),
               largest_tail_p999_us=float(tails.p999_ns.max()/1000),
               min_block_run_ms=float(block.runtime_ms.min()))
    write_json(P/'data/processed/analysis.json',stats)
    mixtable=mix.groupby('read_percent')[['iops','bandwidth_mib_s','combined_mean_latency_ns']].median().reset_index()
    print('Project 3: tables and figures regenerated.')

if __name__=='__main__':main()
