"""Readable report-sized summaries; complete experimental plots remain alongside them."""
from pathlib import Path
import os
ROOT=Path(__file__).resolve().parents[2]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'project1/.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def generate():
    plt.rcParams.update({'font.size':8.7,'axes.titlesize':9.5,'axes.labelsize':8.7,'legend.fontsize':8,'xtick.labelsize':8,'ytick.labelsize':8,'axes.grid':True,'grid.alpha':.2,'figure.constrained_layout.use':True})
    d=pd.read_csv(ROOT/'project1/data/processed/measurements.csv');d=d[(d.build=='native')&(d.dtype=='f32')&d.suites.str.contains('baseline_locality_dtype')]
    fig,ax=plt.subplots(figsize=(6.8,2.3))
    for k in ['axpy','mul','stencil']:
        q=d[d.kernel==k].groupby('working_set_bytes').speedup.agg(['median','std'])
        ax.errorbar(q.index/2**20,q['median'],yerr=q['std'],marker='o',markersize=3,capsize=2,label=k)
    for x,label in [(.125,'P L1D'),(16,'P shared L2')]:ax.axvline(x,color='gray',ls=':',lw=.8);ax.text(x,.025,label,transform=ax.get_xaxis_transform(),va='bottom',ha='left',color='gray',fontsize=7)
    ax.set_xscale('log',base=2);ax.set_xlabel('Active array footprint (MiB)');ax.set_ylabel('Native / scalar speedup');ax.legend(ncol=3,loc='upper right');ax.set_title('Float32, one thread; median +/- sample SD (5 trials)')
    fig.savefig(ROOT/'project1/figures/report_summary.png',dpi=220);plt.close(fig)
    d=pd.read_csv(ROOT/'project2/data/processed/measurements.csv');b=d[(d['mode']=='chase')&d.suites.str.contains('baseline_workingset')]
    fig,axs=plt.subplots(1,2,figsize=(6.8,2.0))
    for pattern in ['sequential','random']:
        q=b[b.pattern==pattern].groupby('bytes').latency_ns.agg(['median','std']);axs[0].errorbar(q.index/2**20,q['median'],yerr=q['std'],marker='o',markersize=2.5,label=pattern)
    axs[0].set_xscale('log',base=2);axs[0].set_yscale('log');axs[0].set_xlabel('Address footprint (MiB)');axs[0].set_ylabel('Dependent ns / load');axs[0].set_title('Working-set regimes');axs[0].legend(fontsize=6.8,loc='upper left')
    t=d[(d['mode']=='traffic')&d.suites.str.contains('intensity')].groupby('threads')[['probe_latency_ns','useful_gib_per_s']].agg(['median','std'])
    axs[1].errorbar(t[('probe_latency_ns','median')],t[('useful_gib_per_s','median')],xerr=t[('probe_latency_ns','std')],yerr=t[('useful_gib_per_s','std')],marker='o',markersize=3,capsize=2)
    for n,offset in [(1,(3,-4)),(2,(-11,-11)),(4,(3,2)),(12,(3,3))]:axs[1].annotate(str(n),(t.loc[n,('probe_latency_ns','median')],t.loc[n,('useful_gib_per_s','median')]),xytext=offset,textcoords='offset points',fontsize=7.5)
    axs[1].set_xlabel('Loaded read probe (ns / load)');axs[1].set_ylabel('Useful GiB/s');axs[1].set_title('Labels: traffic threads; knee = 2')
    fig.savefig(ROOT/'project2/figures/report_summary.png',dpi=220);plt.close(fig)
    q=pd.read_csv(ROOT/'project3/data/processed/queue_curve.csv');p=pd.read_csv(ROOT/'project3/data/processed/parallelism.csv');tails=pd.read_csv(ROOT/'project3/data/processed/tail_counts.csv')
    fig,axs=plt.subplots(1,2,figsize=(6.8,2.2))
    axs[0].errorbar(q.combined_mean_latency_ns_median/1e6,q.iops_median/1000,yerr=q.iops_std/1000,marker='o',markersize=3,capsize=2,label='1 process, QD1-256')
    axs[0].errorbar(p.combined_mean_latency_ns_median/1e6,p.iops_median/1000,yerr=p.iops_std/1000,marker='s',markersize=3,label='QD8, 2-12 processes')
    for depth,label,ofs in [(1,'QD1',(3,-2)),(8,'QD8',(3,3))]:
        r=q[q.requested_qd==depth].iloc[0];axs[0].annotate(label,(r.combined_mean_latency_ns_median/1e6,r.iops_median/1000),xytext=ofs,textcoords='offset points',fontsize=7)
    axs[0].set_xlabel('Mean total latency (ms)');axs[0].set_ylabel('Thousand IOPS');axs[0].set_title('Random 4KiB throughput / latency');axs[0].legend(loc='lower right',fontsize=6.7)
    cols=['p50_ns','p95_ns','p99_ns','p999_ns']
    for name,z in tails.groupby('case_id'):
        med=z[cols].median()/1e6;lo=z[cols].min()/1e6;hi=z[cols].max()/1e6
        axs[1].errorbar(range(4),med,yerr=[med-lo,hi-med],marker='o',markersize=3,capsize=3,label='QD4' if 'mid' in name else 'QD8')
        for _,r in z.iterrows():axs[1].scatter(range(4),r[cols].astype(float)/1e6,s=6,alpha=.5)
    axs[1].set_xticks(range(4),['p50','p95','p99','p99.9']);axs[1].set_yscale('log');axs[1].set_ylabel('Total latency (ms, log)');axs[1].set_title('Tail trials: median and min-max');axs[1].legend(fontsize=7)
    fig.savefig(ROOT/'project3/figures/report_summary.png',dpi=220);plt.close(fig)
if __name__=='__main__':generate()
