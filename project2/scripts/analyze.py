from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'shared'))
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
    lines=['# Project 2 — Cache & Memory Performance Profiling','',
           '## Method and controls','',
           'Native C benchmarks replace Intel MLC, which is not a native Apple Silicon/macOS tool. Exact code, commands, trial seeds, and pre-experiment hypotheses are included.',
           'M3 Pro, 18GB unified memory, macOS 15.6.1, Apple Clang 17.0.0; 128B cache line and 16KiB native pages. P cores: 128KiB L1D and 16MiB shared L2; E cores: 64KiB L1D and 4MiB shared L2.',
           'No fixed-frequency governor, strict pinning, CPU isolation, or NUMA placement is claimed. User-initiated QoS is a hint. Power state and system snapshots are retained before/after each project.',
           'Pointer chains contain all selected nodes in one cycle, with sequential or seeded Fisher–Yates random order. A dependent 64-load unrolled chain approximates low-queue latency. All pages are initialized and the chain is warmed before timing.',
           'Traffic buffers total approximately 256MiB, partitioned across workers. A separate 64MiB random pointer chain measures read latency under load. Timer checks are amortized over load batches; clocks are CLOCK_MONOTONIC_RAW.',
           'Read/write percentages describe source-level 8-byte operations. Writes may trigger read-for-ownership and writeback; useful GiB/s is not measured DRAM bus traffic. Random traffic also reads a precomputed index array, whose size is recorded.',
           'Self-tests validate unique cycles and every read/write mix against a sequential small reference. Five trials per plain configuration are retained; figures show median ± sample SD.',
           '', '## Low-queue baselines and cache transitions','',markdown_table(levels),
           '![Working set](figures/working_set_latency.png)','![Granularity](figures/granularity_latency.png)',
           'These are observed working-set regimes, not isolated physical-level latency constants. No separately exposed L3 was found; the beyond-L2 region may also include Apple system-level cache. The largest range is 256MiB.',
           'Sequential pointer chains can be prefetched. A tiny 64-node randomized cycle produced an unusually low apparent latency; it is retained as an anomaly and excluded from the per-level baseline table. See any supplementary unroll study before assigning a microarchitectural cause.',
           '', '## Patterns, read/write mix, and access intensity','',
           '![Pattern and mix](figures/pattern_rw_granularity.png)','![Throughput-latency](figures/throughput_latency.png)',
           f'The first tested traffic-thread count reaching 90% of the maximum median useful throughput is {knee}. The no-load probe median is {zero:.2f}ns/load. The knee definition is operational and does not prove a device-only saturation threshold.',
           'Loaded latency is the independent read-probe latency, including scheduling interference. It is not the completion or persistence latency of individual store operations. Adding threads can also use E cores; pinning limitations prevent attributing every change solely to DRAM queuing.',
           'Little’s Law is L = lambda W for the same request population in a stable interval. A single dependent DRAM-scale chain has about one request available at a time; its reciprocal latency explains why it cannot reach streaming bandwidth.',
           'For the 100%-read, 64B-spaced stream, two useful 8B accesses can share one 128B line. An illustrative line-demand rate is useful_bytes_per_second / 16, assuming one fetch per line and no extra reuse. Multiplying this by the independent probe latency gives only an approximate concurrency requirement; it is NOT an observed outstanding-request count because probe and stream latencies are different populations.',
           '', '## Cache and TLB counter correlation','',
           'The saved Instruments manual template selects retired L1D load-cache misses, retired L1D TLB misses, L2 data-TLB misses, cycles, instructions, and SIMD/FP arithmetic instructions. Original traces, raw XML, event definitions, exact commands, and executable hashes are preserved.',
           'A byte-identical executable is staged to a temporary path without spaces for reliable xctrace launching. The initial launch from a spaced path stalled and was rejected as a pilot.',
           'Only counter samples whose leaf PC is in chase_batch or mul_f32 are attributed to that kernel. This includes warm-up calls, excludes allocation/driver samples, and is sampled-delta attribution rather than exact whole-process perf-stat totals. Three separate instrumented trials per profile avoid mixing instrumentation overhead into the plain-time sweep.',
           'Miss counts are normalized per 1000 retired instructions. L2_TLB_MISS_DATA has different speculative/retirement semantics from the NONSPEC L1 event; their numerical counts are not assumed to nest.',
           '![Hardware counters](figures/hardware_counters.png)','![Numeric loop](figures/numeric_cache_correlation.png)',
           'AMAT = L1_hit_time + L1_miss_rate * lower_level_penalty is the interpretation model. Misses per instruction are NOT a miss probability per memory access, so that raw denominator cannot directly supply the AMAT probability. The measured latency and counter trends jointly support the locality interpretation.',
           'For the dependent chase only, disassembly verifies 64 loads plus SUBS and B.NE per unrolled loop. Multiplying misses/instruction by 66/64 approximates misses/load, ignoring small bookend/sampling attribution overhead. The following AMAT illustration uses L1 and lower-regime latency endpoints for calibration; it is not an independent predictive validation, and a detailed multilevel model would need L2-cache hit/miss probabilities.',markdown_table(amat),'The two-endpoint AMAT estimate substantially underpredicts the largest case (about 43ns vs 110ns). The counted retired L1 event, sampled instruction attribution, prefetch/speculation and mixed lower-level hit paths do not form a complete probability tree. The discrepancy is retained; it prevents claiming a validated multilevel AMAT model from these counters.',
           '', '## Page locality and huge pages','',
           '![Page locality](figures/page_locality.png)',
           'Clustered and spread variants touch the same number of distinct cache lines. Spread uses one node per 16KiB page; clustered uses 128B spacing. Both cache conflicts and translation pressure can matter, hence the hardware TLB events above are needed rather than treating elapsed time as a TLB count.',
           'The initial spread case used page offset zero for every node, which can also alias L1 sets. An adaptive control distributes offsets as ((node_index * 17) mod 128) * 128 bytes inside each page. It preserves node/page count while balancing the obvious index bits. Both original and controlled data are retained; residual physical coloring and lower-cache effects are not assumed absent.',
           '![Page offset control](figures/page_offset_control.png)','![Tiny-cycle control](figures/tiny_cycle_unroll.png)',
           'The tiny-cycle control changes only the unroll factor (63 versus 64 dependent loads) at 64/128/256 nodes. It is a benchmark-structure check, not a separate cache-capacity measurement; no unsupported microarchitectural mechanism is claimed.',
           f'The native page size is {hug["native_page_bytes"]} bytes. An explicit 2MiB superpage request returned {hug["kern_return"]}: {hug["message"]}. The PDF allows huge pages where available; no huge-page result is fabricated. Native 4KiB pages are not a selectable equivalent on this host.',
           '', '## Misleading benchmark and limitations','',
           '![Cache reuse pitfall](figures/cache_reuse_pitfall.png)',markdown_table(pitfall),
           'The cache-resident and DRAM-scale buffers use the same traffic loop and independent probe. Calling both measurements “DRAM bandwidth” would be misleading. The experimental kernel also includes per-operation control overhead and cannot establish a hardware peak bandwidth by itself.',
           'Unexpected high tails or small-iteration effects are retained, not hidden. Hardware thermal/frequency state, OS interference, prefetching, shared caches, and index-generation traffic limit causal attribution.',
           '', '## Deliverables','',
           'README.md provides build/run/analysis commands. HYPOTHESES.md predates results. AI_USE.md distinguishes agent validation from the student’s required independent review. Plans, raw records, processed tables, plots, PMU evidence and the failed superpage probe are included.']
    (P/'REPORT.md').write_text('\n\n'.join(lines)+'\n')
    print('Project 2 analysis and report generated.')
if __name__=='__main__':main()
