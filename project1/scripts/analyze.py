from pathlib import Path
import json,re,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import plotting,write_json,markdown_table
P=ROOT/'project1';plt=plotting()

def main():
    df=pd.DataFrame([json.loads(p.read_text())['measurement'] for p in sorted((P/'data/raw/runs').glob('*.json'))])
    df['ns_per_call']=df.elapsed_ns/df.iterations
    df['ns_per_element']=df.elapsed_ns/(df.iterations*df.elements_per_iteration)
    df['elements_per_s']=df.iterations*df.elements_per_iteration/(df.elapsed_ns*1e-9)
    df['p_core_cycle_fraction']=df.pcycles/df.cycles
    df['effective_ghz']=df.cycles/df.thread_cpu_ns
    keys=['kernel','dtype','n','stride','offset_elements','trial']
    scalar=df[df.build=='scalar'][keys+['ns_per_call']].rename(columns={'ns_per_call':'scalar_ns_per_call'})
    df=df.merge(scalar,on=keys,validate='many_to_one')
    df['speedup']=df.scalar_ns_per_call/df.ns_per_call
    df.to_csv(P/'data/processed/measurements.csv',index=False)
    metrics=['ns_per_call','ns_per_element','speedup','gflops','gib_per_s','cycles_per_element','elements_per_s','p_core_cycle_fraction','effective_ghz']
    summary=df.groupby(['case_id','kernel','dtype','n','stride','offset_elements','build','working_set_bytes'])[metrics].agg(['median','mean','std','count'])
    summary.columns=['_'.join(c) for c in summary.columns];summary=summary.reset_index()
    summary.to_csv(P/'data/processed/summary.csv',index=False)
    baseline=df[df.suites.str.contains('baseline_locality_dtype')]
    for metric,label,filename in [('speedup','Speedup vs scalar','baseline_speedup'),('gflops','Throughput (GFLOP/s)','baseline_throughput'),('cycles_per_element','CPU cycles / element','cycles_per_element')]:
        fig,axs=plt.subplots(2,3,figsize=(13,7))
        for i,dtype in enumerate(['f32','f64']):
            for j,kernel in enumerate(['axpy','mul','stencil']):
                ax=axs[i,j]
                for build in ['scalar','auto','native']:
                    x=baseline[(baseline.kernel==kernel)&(baseline.dtype==dtype)&(baseline.build==build)].groupby('working_set_bytes')[metric].agg(['median','std'])
                    ax.errorbar(x.index/1024,x['median'],yerr=x['std'],marker='o',capsize=2,label=build)
                ax.set_xscale('log',base=2);ax.set_title(f'{kernel}, {dtype}');ax.set_xlabel('Active array footprint (KiB)');ax.set_ylabel(label)
                for size,style in [(128,':'),(16384,'--')]:ax.axvline(size,color='gray',ls=style,lw=.8)
                if metric=='speedup':ax.axhline(1,color='black',lw=.5)
                if i==0 and j==0:ax.legend()
        fig.suptitle('Single thread; medians ± sample SD (5 trials). Gray: P-core L1D / shared L2 capacities.')
        fig.savefig(P/f'figures/{filename}.png');plt.close(fig)
    align=df[df.suites.str.contains('alignment_tail')]
    fig,axs=plt.subplots(1,2,figsize=(12,4))
    ns=[64,65,1024,1025,65536,65537]
    for ax,dtype in zip(axs,['f32','f64']):
        for build,offset in __import__('itertools').product(['scalar','auto','native'],[0,1]):
            s=align[(align.dtype==dtype)&(align.build==build)&(align.offset_elements==offset)].groupby('n').ns_per_element.agg(['median','std']).reindex(ns)
            ax.errorbar(np.arange(len(ns)),s['median'],yerr=s['std'],marker='o',ls='--' if offset else '-',label=f'{build}, offset {offset}')
        ax.set_xticks(range(len(ns)),[str(n) for n in ns],rotation=35);ax.set_xlabel('N (paired divisible / remainder sizes)');ax.set_ylabel('ns / element');ax.set_title(dtype)
    axs[1].legend(fontsize=8,ncol=2);fig.savefig(P/'figures/alignment_tail.png');plt.close(fig)
    stride=df[df.suites.str.contains('stride')]
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for ax,n in zip(axs,[65536,4194304]):
        for build in ['scalar','auto','native']:
            s=stride[(stride.n==n)&(stride.build==build)].groupby('stride').gib_per_s.agg(['median','std'])
            ax.errorbar(s.index,s['median'],yerr=s['std'],marker='o',capsize=3,label=build)
        ax.set_xticks([1,2,4,8]);ax.set_xlabel('Element stride');ax.set_ylabel('Useful traffic (GiB/s)');ax.set_title(f'Multiply f32, N={n:,}');ax.legend()
    fig.savefig(P/'figures/stride.png');plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(13,4))
    for ax,k in zip(axs,['axpy','mul','stencil']):
        for dtype in ['f32','f64']:
            s=baseline[(baseline.kernel==k)&(baseline.build=='native')&(baseline.dtype==dtype)].groupby('n').elements_per_s.agg(['median','std'])
            ax.errorbar(s.index,s['median']/1e9,yerr=s['std']/1e9,marker='o',label=dtype)
        ax.set_xscale('log',base=2);ax.set_xlabel('N');ax.set_ylabel('Billion elements/s');ax.set_title(k);ax.legend()
    fig.savefig(P/'figures/data_type.png');plt.close(fig)
    negative=df[df.kernel=='dot'];negative.groupby(['dtype','n','build'])[['speedup','cycles_per_element']].agg(['median','std']).to_csv(P/'data/processed/negative_case.csv')
    streams=[];peaks=[]
    for trial in range(5):
        text=json.loads((P/f'data/raw/stream-{trial}.json').read_text())['stdout']
        row={'trial':trial}
        for k in ['Copy','Scale','Add','Triad']:
            m=re.search(r'^'+k+r':\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)',text,re.M)
            row[k+'_MB_s']=float(m.group(1));row[k+'_avg_s']=float(m.group(2))
        row['correctness']='Solution Validates' in text;streams.append(row)
        path=P/f'data/raw/peak-{trial}.json'
        if path.exists():peaks.append(json.loads(json.loads(path.read_text())['stdout']))
    pd.DataFrame(streams).to_csv(P/'data/processed/bandwidth_reference.csv',index=False)
    if not peaks:raise RuntimeError('Validated compute-ceiling data still missing')
    pd.DataFrame(peaks).to_csv(P/'data/processed/compute_ceiling.csv',index=False)
    bandwidth=float(np.median([x['Copy_MB_s'] for x in streams]))*1e6
    peak=float(np.median([x['gflops'] for x in peaks]))
    roof=[]
    for kernel,flops,bytes_ in [('axpy',2,12),('mul',1,12),('stencil',5,8)]:
        s=baseline[(baseline.kernel==kernel)&(baseline.dtype=='f32')&(baseline.build=='native')&(baseline.n==16777216)]
        ai=flops/bytes_;bound=min(peak,bandwidth*ai/1e9)
        roof.append(dict(kernel=kernel,dtype='f32',arithmetic_intensity=ai,measured_gflops=float(s.gflops.median()),bound_gflops=bound,
                         bandwidth_bytes_s=bandwidth,compute_ceiling_gflops=peak))
    pd.DataFrame(roof).to_csv(P/'data/processed/roofline.csv',index=False)
    x=np.logspace(-2,2,300);fig,ax=plt.subplots(figsize=(8,5))
    ax.loglog(x,np.minimum(peak,bandwidth*x/1e9),label='Empirical roofline reference')
    for r in roof:
        ax.scatter(r['arithmetic_intensity'],r['measured_gflops']);ax.annotate(r['kernel'],(r['arithmetic_intensity'],r['measured_gflops']),xytext=(5,5),textcoords='offset points')
    ax.set_xlabel('Algorithmic FLOP / useful byte');ax.set_ylabel('GFLOP/s');ax.set_title('f32, largest working set; STREAM useful-byte bandwidth')
    ax.legend();fig.savefig(P/'figures/roofline.png');plt.close(fig)
    evidence=[]
    for build in ['scalar','auto','native']:
        text=(P/f'evidence/{build}-vectorization.txt').read_text()
        dis=(P/f'evidence/{build}-disassembly.txt').read_text()
        evidence.append(dict(build=build,vectorized_remarks=text.count('remark: vectorized loop'),
                             nonvectorized_remarks=text.count('remark: loop not vectorized'),
                             vector_f32_instructions=bool(re.search(r'\b(?:fmul|fadd)\.4s\b',dis)),
                             vector_f64_instructions=bool(re.search(r'\b(?:fmul|fadd)\.2d\b',dis)),
                             fma_present=bool(re.search(r'\bfmla',dis))))
    write_json(P/'evidence/vectorization-summary.json',evidence)
    stats=dict(rows=len(df),cases=df.case_id.nunique(),trials=5,all_correct=bool(df.correctness.all()),
               all_cycles_available=bool(df.cycles_available.all()),
               lowest_p_core_fraction=float(df.p_core_cycle_fraction.min()),
               rows_below_90pct_pcore=int((df.p_core_cycle_fraction<.9).sum()),
               min_thread_cpu_to_wall=float((df.thread_cpu_ns/df.elapsed_ns).min()),
               effective_ghz_min=float(df.effective_ghz.min()),effective_ghz_max=float(df.effective_ghz.max()),
               empirical_compute_ceiling_gflops=peak,copy_bandwidth_GB_s=bandwidth/1e9)
    write_json(P/'data/processed/analysis.json',stats)
    # Quantitative comparisons use only recorded medians, without excluding outliers.
    comparison=baseline[(baseline.build=='native') & baseline.n.isin([1024,16777216])].groupby(['kernel','dtype','n'])[['speedup','gflops','gib_per_s']].median().reset_index()
    comparison.to_csv(P/'data/processed/key_comparisons.csv',index=False)
    negrows=[]
    for path in sorted((P/'data/raw/negative').glob('*.json')):
        d=json.loads(path.read_text());m=json.loads(d['stdout']);m['trial']=int(path.stem.rsplit('-r',1)[1]);negrows.append(m)
    neg=pd.DataFrame(negrows)
    if len(neg):
        neg.to_csv(P/'data/processed/negative_control.csv',index=False)
        nt=neg.groupby(['n','build']).ns_per_element.median().unstack()
        nt['auto_speedup']=nt.scalar/nt.auto;nt['native_speedup']=nt.scalar/nt.native
        nt=nt.reset_index()
    alignmed=align.groupby(['dtype','build','n','offset_elements']).ns_per_element.median()
    alignrows=[]
    for dtype in ['f32','f64']:
        for n in [64,65,1024,1025,65536,65537]:
            a=alignmed.loc[(dtype,'native',n,0)];b=alignmed.loc[(dtype,'native',n,1)]
            alignrows.append(dict(dtype=dtype,n=n,aligned_ns_element=a,shifted_ns_element=b,shifted_over_aligned=b/a))
    at=pd.DataFrame(alignrows);at.to_csv(P/'data/processed/alignment_ratios.csv',index=False)
    sr=stride[stride.build=='native'].groupby(['n','stride'])[['gib_per_s','speedup']].median().reset_index()
    sr.to_csv(P/'data/processed/stride_comparison.csv',index=False)
    # Concise generated report keeps every figure tied to its raw data and formulas.
    print('Project 1: tables and figures regenerated.')

if __name__=='__main__':main()
