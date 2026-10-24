from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import plotting,write_json,markdown_table
P=ROOT/'project2';plt=plotting()

def main():
    df=pd.DataFrame([json.loads(p.read_text())['measurement'] for p in sorted((P/'data/raw/runs').glob('*.json'))]);df.to_csv(P/'data/processed/measurements.csv',index=False)
    chase=df[df['mode']=='chase'];traffic=df[df['mode']=='traffic']
    groups=['case_id','mode','bytes','spacing','pattern']
    metrics=['latency_ns','cycles_per_load','probe_latency_ns','useful_gib_per_s','traffic_reads','traffic_writes','process_cycles','process_instructions']
    summary=df.groupby(groups)[metrics].agg(['median','std','count']);summary.columns=['_'.join(c) for c in summary.columns];summary.reset_index().to_csv(P/'data/processed/summary.csv',index=False)
    base=chase[chase.suites.str.contains('baseline_workingset')]
    fig,ax=plt.subplots(figsize=(9,5))
    for pattern in ['sequential','random']:
        s=base[base.pattern==pattern].groupby('bytes').latency_ns.agg(['median','std'])
        ax.errorbar(s.index/1024,s['median'],yerr=s['std'],marker='o',capsize=3,label=pattern)
    for kb,label in [(64,'E L1D'),(128,'P L1D'),(4096,'E shared L2'),(16384,'P shared L2')]:
        ax.axvline(kb,color='gray',ls=':',lw=.8);ax.text(kb,ax.get_ylim()[1]*.85,label,rotation=90,fontsize=8)
    ax.set_xscale('log',base=2);ax.set_yscale('log');ax.set_xlabel('Address footprint (KiB)');ax.set_ylabel('ns / dependent load');ax.set_title('Dependent-chain latency: median ± SD, 5 trials');ax.legend()
    fig.savefig(P/'figures/working_set_latency.png');plt.close(fig)
    gran=chase[chase.suites.str.contains('granularity')]
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for ax,size in zip(axs,[65536,268435456]):
        for pattern in ['sequential','random']:
            s=gran[(gran.bytes==size)&(gran.pattern==pattern)].groupby('spacing').latency_ns.agg(['median','std'])
            ax.errorbar(s.index,s['median'],yerr=s['std'],marker='o',label=pattern)
        ax.set_xscale('log',base=2);ax.set_xlabel('Node spacing (bytes)');ax.set_ylabel('ns / load');ax.set_title(f'Footprint {size/1024**2:g} MiB');ax.legend()
    fig.savefig(P/'figures/granularity_latency.png');plt.close(fig)
    matrix=traffic[traffic.suites.str.contains('pattern_granularity_rw')]
    fig,axs=plt.subplots(2,2,figsize=(11,8))
    for j,pattern in enumerate(['sequential','random']):
        for pct in [0,50,70,100]:
            s=matrix[(matrix.pattern==pattern)&(matrix.read_percent==pct)].groupby('spacing')[['useful_gib_per_s','probe_latency_ns']].agg(['median','std'])
            for i,(metric,label) in enumerate([('useful_gib_per_s','Useful GiB/s'),('probe_latency_ns','Independent loaded-probe ns/load')]):
                ax=axs[i,j];ax.errorbar(s.index,s[(metric,'median')],yerr=s[(metric,'std')],marker='o',label=f'{pct}% read');ax.set_xscale('log',base=2);ax.set_xlabel('Access spacing (bytes)');ax.set_ylabel(label);ax.set_title(pattern);ax.legend(fontsize=8)
    fig.suptitle('256MiB load + 64MiB probe; one traffic thread; 8 useful bytes per source operation')
    fig.savefig(P/'figures/pattern_rw_granularity.png');plt.close(fig)
    intensity=traffic[traffic.suites.str.contains('intensity')]
    s=intensity.groupby('threads')[['useful_gib_per_s','probe_latency_ns']].agg(['median','std'])
    zero=chase[chase.suites.str.contains('intensity_zero')].latency_ns.median()
    knee=int(s.index[s[('useful_gib_per_s','median')]>=.9*s[('useful_gib_per_s','median')].max()][0])
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    axs[0].errorbar(s.index,s[('useful_gib_per_s','median')],yerr=s[('useful_gib_per_s','std')],marker='o');axs[0].set_xlabel('Traffic threads (+ one latency probe)');axs[0].set_ylabel('Useful GiB/s')
    axs[0].axvline(knee,color='red',ls='--',label=f'90%-of-max knee: {knee}');axs[0].legend()
    axs[1].errorbar(s[('probe_latency_ns','median')],s[('useful_gib_per_s','median')],xerr=s[('probe_latency_ns','std')],yerr=s[('useful_gib_per_s','std')],marker='o')
    for t in s.index:axs[1].annotate(str(int(t)),(s.loc[t,('probe_latency_ns','median')],s.loc[t,('useful_gib_per_s','median')]),xytext=(4,4),textcoords='offset points')
    axs[1].axvline(zero,color='gray',ls=':',label='No-load probe latency');axs[1].set_xlabel('Independent probe latency (ns/load)');axs[1].set_ylabel('Useful GiB/s');axs[1].legend(fontsize=8)
    fig.savefig(P/'figures/throughput_latency.png');plt.close(fig)
    s.columns=['_'.join(c) for c in s.columns];s.reset_index().to_csv(P/'data/processed/intensity.csv',index=False)
    page=chase[chase.suites.str.contains('page_locality')]
    fig,ax=plt.subplots(figsize=(8,5))
    for spacing,label in [(128,'Clustered: 128B spacing'),(16384,'Spread: one node / 16KiB page')]:
        q=page[page.spacing==spacing].groupby('nodes').latency_ns.agg(['median','std'])
        ax.errorbar(q.index,q['median'],yerr=q['std'],marker='o',label=label)
    follow=pd.read_csv(P/'data/processed/followup.csv')
    balanced=follow[follow.study=='balanced_pages']
    q=balanced.groupby('nodes').latency_ns.agg(['median','std'])
    ax.errorbar(q.index,q['median'],yerr=q['std'],marker='s',label='Spread: balanced offsets inside pages')
    ax.set_xscale('log',base=2);ax.set_xlabel('Touched cache lines / pointer nodes');ax.set_ylabel('ns / dependent load');ax.legend();ax.set_title('Equal touched-line count; different page locality')
    fig.savefig(P/'figures/page_locality.png');plt.close(fig)
    pit=traffic[traffic.suites.str.contains('pitfall_cache_reuse')]
    dram=matrix[(matrix.pattern=='sequential')&(matrix.spacing==64)&(matrix.read_percent==100)]
    pitfall=pd.DataFrame([{'label':'Cache reuse, 64KiB load','median_useful_GiB_s':pit.useful_gib_per_s.median(),'std':pit.useful_gib_per_s.std()},
                          {'label':'DRAM-scale, 256MiB load','median_useful_GiB_s':dram.useful_gib_per_s.median(),'std':dram.useful_gib_per_s.std()}])
    pitfall.to_csv(P/'data/processed/pitfall.csv',index=False)
    fig,ax=plt.subplots(figsize=(7,4));ax.bar(pitfall.label,pitfall.median_useful_GiB_s,yerr=pitfall['std'],capsize=5);ax.set_ylabel('Useful GiB/s (not measured bus traffic)');ax.set_title('A small reused buffer is not a DRAM bandwidth test')
    fig.savefig(P/'figures/cache_reuse_pitfall.png');plt.close(fig)
    counter_rows=[];counter_records=[]
    for path in sorted((P/'data/raw/counters').glob('*.json')):
        d=json.loads(path.read_text())
        if d.get('status')!='success':continue
        counter_records.append(d)
        c=d['case'];v=d['event_sums'];inst=v['Instructions'];r=dict(case_id=c['id'],trial=d['trial'],suite=c['suite'],sample_count=d['sample_count'],sampled_instructions=inst,sampled_cycles=v['Cycles'],p_core_sample_fraction=d['p_core_sample_fraction'],bytes=c.get('bytes'),spacing=c.get('spacing'),nodes=c.get('nodes'),n=c.get('n'))
        for name in ['L1D_CACHE_MISS_LD_NONSPEC','L1D_TLB_MISS_NONSPEC','L2_TLB_MISS_DATA','INST_SIMD_ALU']:
            r[name]=v[name];r[name+'_per_ki']=v[name]/inst*1000
        out=path.with_name(path.stem+'-target.stdout').read_text()
        m=json.loads(next(line for line in out.splitlines() if line.startswith('{')))
        r.update(instrumented_elapsed_ns=m['elapsed_ns'],instrumented_latency_ns=m.get('latency_ns'),instrumented_ns_per_element=(m['elapsed_ns']/(m['iterations']*m['elements_per_iteration'])) if 'iterations' in m else None)
        counter_rows.append(r)
    if not counter_rows:raise RuntimeError('Hardware counter data missing')
    write_json(P/'data/processed/counter-summary.json',counter_records)
    counters=pd.DataFrame(counter_rows);counters.to_csv(P/'data/processed/counters.csv',index=False)
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for ax,suite,metric,ylabel in [(axs[0],'cache','L1D_CACHE_MISS_LD_NONSPEC_per_ki','Retired L1D load misses / 1000 instructions'),(axs[1],'TLB','L1D_TLB_MISS_NONSPEC_per_ki','Retired L1D TLB misses / 1000 instructions')]:
        z=counters[counters.suite==suite]
        if suite=='cache':
            q=z.groupby('bytes')[metric].agg(['median','std']);ax.errorbar(q.index/1024,q['median'],yerr=q['std'],marker='o');ax.set_xlabel('Address footprint (KiB)')
        else:
            for z0,label in [(z[z.spacing==128],'Clustered 128B'),(z[z.spacing==16384],'Spread, offset zero'),(counters[counters.suite=='TLB-balanced'],'Spread, balanced offsets')]:
                q=z0.groupby('nodes')[metric].agg(['median','std']);ax.errorbar(q.index,q['median'],yerr=q['std'],marker='o',label=label)
            ax.set_xlabel('Touched lines / nodes');ax.legend(fontsize=8)
        ax.set_xscale('log',base=2);ax.set_ylabel(ylabel)
    fig.suptitle('Separate Instruments runs, medians ± SD, 3 trials; kernel-leaf attribution')
    fig.savefig(P/'figures/hardware_counters.png');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    z=counters[counters.suite=='numeric_cache']
    for ax,metric,label in [(axs[0],'instrumented_ns_per_element','Instrumented ns / element'),(axs[1],'L1D_CACHE_MISS_LD_NONSPEC_per_ki','Retired L1D load misses / 1000 instructions')]:
        q=z.groupby('n')[metric].agg(['median','std']);ax.bar([str(int(n)) for n in q.index],q['median'],yerr=q['std'],capsize=4);ax.set_xlabel('Multiply float32 N');ax.set_ylabel(label)
    fig.savefig(P/'figures/numeric_cache_correlation.png');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for ax,metric,label in [(axs[0],'L1D_CACHE_MISS_LD_NONSPEC_per_ki','Retired L1D load misses / 1000 instructions'),(axs[1],'L1D_TLB_MISS_NONSPEC_per_ki','Retired L1D TLB misses / 1000 instructions')]:
        for suite,spacing,title in [('TLB',128,'Clustered'),('TLB',16384,'Spread, offset zero'),('TLB-balanced',16384,'Spread, balanced offsets')]:
            q=counters[(counters.suite==suite)&(counters.spacing==spacing)].groupby('nodes')[metric].agg(['median','std'])
            ax.errorbar(q.index,q['median'],yerr=q['std'],marker='o',label=title)
        ax.set_xscale('log',base=2);ax.set_xlabel('Touched lines / nodes');ax.set_ylabel(label);ax.legend(fontsize=8)
    fig.savefig(P/'figures/page_offset_control.png');plt.close(fig)
    tiny=follow[follow.study=='tiny_cycle']
    fig,ax=plt.subplots(figsize=(8,4))
    for unroll in [63,64]:
        q=tiny[tiny.unroll==unroll].groupby('nodes').latency_ns.agg(['median','std']);ax.errorbar(q.index,q['median'],yerr=q['std'],marker='o',label=f'{unroll} dependent loads per loop')
    ax.set_xlabel('Pointer-cycle nodes');ax.set_ylabel('Apparent ns / load');ax.legend();ax.set_title('Tiny-cycle anomaly control: same nodes, different unroll')
    fig.savefig(P/'figures/tiny_cycle_unroll.png');plt.close(fig)
    levels=[]
    for label,size in [('P-core-L1-scale',65536),('L2-scale',1048576),('Beyond local L2 / possible SLC',33554432),('DRAM-scale',268435456)]:
        q=base[(base.pattern=='random')&(base.bytes==size)];levels.append(dict(region=label,footprint_bytes=size,median_ns=q.latency_ns.median(),std_ns=q.latency_ns.std(),median_cycles=q.cycles_per_load.median()))
    levels=pd.DataFrame(levels);levels.to_csv(P/'data/processed/latency_baselines.csv',index=False)
    # Approximate load denominator from the verified 64 LDR + SUBS + B.NE loop.
    # Endpoint latencies calibrate this illustration; this is not an independent AMAT prediction.
    l1=float(levels.iloc[0].median_ns);l2=float(levels.iloc[1].median_ns);dram_lat=float(levels.iloc[-1].median_ns)
    amat=[]
    for size,g in counters[counters.suite=='cache'].groupby('bytes'):
        miss=float((g.L1D_CACHE_MISS_LD_NONSPEC/g.sampled_instructions*66/64).median())
        penalty=(dram_lat if size>=268435456 else l2)-l1
        observed=float(base[(base.bytes==size)&(base.pattern=='random')].latency_ns.median())
        amat.append(dict(footprint_bytes=int(size),approx_L1_miss_probability=miss,assumed_lower_penalty_ns=penalty,
                         illustrative_AMAT_ns=l1+miss*penalty,observed_plain_ns=observed))
    amat=pd.DataFrame(amat);amat.to_csv(P/'data/processed/amat_illustration.csv',index=False)
    hug=json.loads(json.loads((P/'evidence/hugepage.json').read_text())['stdout'])
    stats=dict(rows=len(df),cases=df.case_id.nunique(),all_correct=bool(df.correctness.all()),native_page_bytes=16384,
               hugepage=hug,traffic_knee_threads=knee,no_load_probe_ns=float(zero),counter_runs=len(counters),
               minimum_counter_samples=int(counters.sample_count.min()),
               minimum_core_p_fraction=float(counters.p_core_sample_fraction.min()))
    write_json(P/'data/processed/analysis.json',stats)
    print('Project 2: tables and figures regenerated.')

if __name__=='__main__':main()
