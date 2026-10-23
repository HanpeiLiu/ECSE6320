from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'shared'))
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
    lines=['# Project 3 — SSD Performance Profiling','',
           '## Safe scope and method','',
           'APPLE SSD AP1024Z, approximately 1TB, internal Apple Fabric/NVMe controller, APFS on macOS 15.6.1, M3 Pro CPU. Native block size reported by diskutil: 4096B. Exact system and tool versions are retained in environment records.',
           'All writes target only project3/work/ssd-test.bin or verify.bin, newly created under an ownership marker. Raw device writes and arbitrary file paths are not accepted. The data file is 1GiB; no partition was changed.',
           'FIO 3.43, posixaio; primary runs use direct=1, implemented by F_NOCACHE on macOS, and 16KiB memory alignment. This is a filesystem-level measurement, not a raw flash or standard PCIe-lane benchmark.',
           'A separate 64MiB CRC32C write/read verification passed before the data-file initialization. The main file was fully written with incompressible buffers and flushed once before the matrix.',
           'refill_buffers=1 and buffer_compress_percentage=0 are held fixed. This adds CPU work, so observed maxima include FIO, OS, and filesystem overhead. Random seeds and every generated .fio configuration are retained.',
           'Each matrix run is bounded by 1s and an I/O-byte cap (2GiB for write/mixed, 4GiB for read), whichever finishes first. No time-based unlimited writes or uncounted ramp writes are used. Three shuffled trials per case expose variability.',
           f'Actual test writes including initialization/CRC verification: {writes/1024**3:.3f}GiB, below the 104GiB enforced budget. The shortest block-matrix run lasted {stats["min_block_run_ms"]:.0f}ms; these are controlled burst/current-state tests, not steady-state certification.',
           'Primary write latency is FIO completion latency with page-cache bypass; no per-I/O fsync is used. Completion is NOT claimed to prove NAND persistence. Total lat_ns includes submission and completion; clat_ns is separately retained.',
           '', '## QD=1 baselines','',markdown_table(table),'![Baselines](figures/zero_queue.png)',
           'The table reports medians of trial percentiles, not a percentile of pooled requests. Each raw JSON+ retains latency histograms and counts. QD=1 limits this application to one outstanding I/O, not all system/background device traffic.',
           '', '## Block size, pattern, and read/write mix','',
           '![Block size](figures/block_size_pattern.png)','![Mix](figures/read_write_mix.png)',markdown_table(mixtable),
           'Block-matrix throughput and latency come from the same runs at fixed QD=1. The mix comparison uses random 4KiB at QD16, including pure-read and pure-write endpoints. Mixed latency is weighted by completion count; read/write percentiles remain separate rather than being averaged together.',
           '', '## Throughput–latency knee and actual concurrency','',
           '![Queue depth and parallelism](figures/throughput_latency.png)',
           f'The single-process operational knee is the smallest tested QD reaching 90% of that curve’s maximum median IOPS: QD{knee}. This definition includes measurement uncertainty and does not establish a raw hardware saturation knee.',
           'Requested QD32–256 did not produce those effective depths: lambda × mean total latency stayed near 16. The raw iodepth_level distributions corroborate the engine/OS limitation. Treating requested QD256 as achieved hardware QD256 would be misleading.',
           'A read-only follow-up uses 2, 4, 8 and 12 forked FIO processes, each at QD8 and with disjoint aligned portions of the same aggregate 1GiB file range. Threads in a single process would not test beyond a per-process limit. Its exact adaptive plan is saved separately.',
           'Forked-process medians remain approximately 53k IOPS as estimated concurrency increases from 16 to 90 and latency grows from 300 to 1,706µs. This supports a plateau in the measured host/filesystem workload; it does not isolate flash-controller limits. Merely adding processes makes response time worse here.',
           'Little’s Law: L=lambda W. Here lambda is the same job group’s completion IOPS and W its count-weighted mean total latency in seconds. The estimate refers to application request lifetime; it is not a direct measurement of the SSD controller’s NVMe queue occupancy. Finite run boundaries and submission overhead cause small deviations.',
           f'The highest individual observed random-read rate was {stats["maximum_observed_random_read_iops"]:,.0f} IOPS; the highest observed sequential read throughput was {stats["maximum_observed_sequential_mib_s"]:,.1f}MiB/s. These are observed host-stack results, not a proven device specification or an interface ceiling.',
           'The controller is exposed as Apple Fabric, without a standard public PCIe link-width/speed ceiling in the collected metadata. We therefore do not invent a numerical PCIe ceiling. Controller parallelism, OS AIO limits, filesystem work, CPU overhead and finite test range all bound the observation.',
           '', '## Tail latency, range, and device state','',
           '![Tail percentiles](figures/tail_latency.png)','![Tail histogram](figures/tail_histogram.png)',
           f'Longer read-only confirmations at mid QD and near the single-process knee each completed at least {stats["minimum_tail_io_count"]:,} requests per trial. The p99.9 tail therefore has at least about {stats["minimum_p999_tail_expected_samples"]:.0f} observations beyond its cutoff; this is more credible than tiny tests but not a confidence guarantee.',
           'All three tail trials are plotted, including the large outlier; whiskers show the observed min–max range. JSON+ histograms are pooled only for the completion-latency survival plot, which is explicitly different from total-latency percentile plots.',
           f'The largest trial p99.9 was {stats["largest_tail_p999_us"]:,.1f}µs. A transient OS scheduling/background-I/O or device-management event is plausible; the available evidence does not isolate garbage collection as the cause. It is retained, not discarded.',
           '![Range and buffered pitfall](figures/range_and_cache_pitfall.png)',
           'The range sweep uses 64MiB, 256MiB and 1GiB logical file ranges. APFS physical placement is not controlled, so these are not known contiguous LBA spans. Buffered 64MiB reads are explicitly warmed before the intentional page-cache pitfall.',
           f'Read-only SMART snapshots before/after each run recorded {stats["temperature_min_C"]:.0f}–{stats["temperature_max_C"]:.0f}°C. No claim of thermal throttling follows from temperature alone. Unsupported NVMe error-log retrieval is avoided by requesting only supported health/attribute logs.',
           'The drive was in its existing used state, not fresh or secure-erased. Full-device preconditioning and deliberate SLC-cache exhaustion are omitted to honor the small, bounded study. Burst vs sustained effects are discussed as limitations; unobserved steady state is not presented as measured.',
           '', '## Reproduction and deliverables','',
           'See README.md, HYPOTHESES.md, AI_USE.md, config/generated/*.fio, all plans, raw JSON+/metadata, the write ledger, processed CSVs and plotting code. All required percentiles and sample counts are retained; no failing I/O result is silently accepted.']
    (P/'REPORT.md').write_text('\n\n'.join(lines)+'\n')
    print('Project 3 analysis, figures, and report generated.')

if __name__=='__main__':main()
