"""Create the concise three-project report from retained processed measurements."""
from pathlib import Path
import csv,json,statistics
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.colors import HexColor,white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader
ROOT=Path(__file__).resolve().parents[2]
import subprocess,sys
plot_python=ROOT/'.venv/bin/python'
subprocess.run([str(plot_python) if plot_python.exists() else sys.executable,str(Path(__file__).with_name('report_figures.py'))],check=True)
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleLocal',fontName='Helvetica-Bold',fontSize=19,leading=23,textColor=HexColor('#17384c'),spaceAfter=8))
styles.add(ParagraphStyle(name='BodyLocal',fontName='Helvetica',fontSize=9.1,leading=12,spaceAfter=6))
styles.add(ParagraphStyle(name='SmallLocal',fontName='Helvetica',fontSize=7.4,leading=9.4,textColor=HexColor('#465865'),spaceAfter=5))
styles.add(ParagraphStyle(name='SubLocal',fontName='Helvetica-Bold',fontSize=10.5,leading=13,spaceBefore=5,spaceAfter=4,textColor=HexColor('#17384c')))
story=[]
def para(text,style='BodyLocal'):story.append(Paragraph(text,styles[style]))
def section(title,text):para(title,'SubLocal');para(text)
def data(path):
    with (ROOT/path).open() as f:return list(csv.DictReader(f))
def js(path):return json.loads((ROOT/path).read_text())
def table(rows,widths):
    cells=[[Paragraph(str(c),styles['SmallLocal']) for c in row] for row in rows]
    t=Table(cells,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#e9f0f4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,HexColor('#9db0bd')),('LINEBELOW',(0,1),(-1,-1),.25,HexColor('#dce4e9')),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),3)]));story.extend([t,Spacer(1,5)])
def picture(path,width):
    p=ROOT/path;w,h=ImageReader(str(p)).getSize();return Image(str(p),width=width,height=width*h/w)
def pair(a,b):
    t=Table([[picture(a,248),picture(b,248)]],colWidths=[255,255]);t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]));story.append(t)
def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(HexColor('#dce4e9'));canvas.line(42,35,570,35);canvas.setFont('Helvetica',7.3);canvas.setFillColor(HexColor('#465865'))
    canvas.drawString(42,23,'ECSE 4320/6320 | Collected 2026-10-23 | Full data and plots accompany this report')
    canvas.drawRightString(570,23,str(doc.page));canvas.restoreState()

a1=js('project1/data/processed/analysis.json');a2=js('project2/data/processed/analysis.json');a3=js('project3/data/processed/analysis.json')
para('Project 1 | SIMD advantage','TitleLocal')
para('System: M3 Pro (6 P + 6 E cores; 12 physical/logical), 18GB, macOS 15.6.1, Xcode 26.3 / Apple Clang 17.0.0. NEON is 128-bit.','SmallLocal')
section('Hypothesis','Regular float32 loops should gain more than float64; larger footprints, strides and ordered reductions should compress SIMD gains.')
section('Method','AXPY, multiply and stencil were tested with scalar, auto and native builds: -O3 -ffp-contract=off; scalar disables loop/SLP vectors, native adds -mcpu=native; no fast-math/LTO. Initialized 128B-aligned arrays, warmup and reference checks precede ~30ms batches. Five shuffled trials; plots use median +/- sample SD; cycles come from real rusage deltas.')
story.append(picture('project1/figures/report_summary.png',510))
para('Figure 1. Native float32 speedup across active footprints; gray lines mark P-core L1D (128KiB) and shared L2 (16MiB). Full scalar/auto/native and float64 plots accompany the report.','SmallLocal')
rows=[['Native / scalar median speedup','f32, N=1,024','f32, N=16,777,216','f64, N=16,777,216']]
k=data('project1/data/processed/key_comparisons.csv')
for kernel in ['axpy','mul','stencil']:
    def speed(dtype,n):return float(next(r for r in k if r['kernel']==kernel and r['dtype']==dtype and int(r['n'])==n)['speedup'])
    rows.append([kernel,f'{speed("f32",1024):.2f}x',f'{speed("f32",16777216):.2f}x',f'{speed("f64",16777216):.2f}x'])
table(rows,[175,105,120,110])
section('Interpretation','AXPY/multiply gains shrink as movement grows; stencil remains near 3.3x in float32. Lane counts (4 float32 / 2 float64) do not guarantee equal speedup. For large multiply, stride 1 to 8 reduces useful throughput from 106 to 10.2GiB/s and native speedup to ~0.99x. Shifted AXPY addresses cost about 10-47% in tested cases; N/N+1 effects include tails and loop overhead.')
para(f'STREAM Copy measured {a1["copy_bandwidth_GB_s"]:.1f}GB/s; 16 verified register FMAs estimate {a1["empirical_compute_ceiling_gflops"]:.1f}GFLOP/s. Float32 arithmetic intensities are AXPY 2/12, multiply 1/12, stencil 5/8 FLOP/B. Roofline measured values are 20.0, 9.1 and 49.0GFLOP/s: memory traffic constrains low-intensity loops. AXPY exceeds the Copy-derived line by ~12%, so it is an approximate traffic-dependent reference.')
section('Verification','All 1,200 primary rows and 324 boundary checks passed. Compiler remarks/disassembly verify vector width and scalar tails. The compute-ceiling loop contains the expected 16 vector FMAs.')
section('Negative case','Ordinary dot uses SIMD products but serial additions (~1.00-1.09x); 30 volatile-accumulator controls verify an explicit non-vectorized loop. The incorrect 9-FMA pilot was rejected. Two migrated rows remain included.')
para('Additional required figures: baseline_speedup, baseline_throughput, cycles_per_element, alignment_tail, stride, data_type, roofline (project1/figures/). Detailed numbers and negative-control evidence remain with the project.','SmallLocal')
story.append(PageBreak())

para('Project 2 | Cache and memory','TitleLocal')
section('Hypothesis','Random dependent loads should slow beyond local caches; concurrency should initially increase bandwidth, then loaded latency. Page spreading should increase translation pressure, with cache conflicts as a confounder.')
section('Method','Native C equivalents of MLC use prefaulted, warmed seeded chains and real cycle counters. Pages are 16KiB; cache lines are 128B. P-core L1D/shared L2 are 128KiB/16MiB; E-core equivalents are 64KiB/4MiB. No isolated L3 is exposed. The matrix has 355 rows (71 cases x5): sequential/random, 64/256/1024B spacings, 100/0, 0/100, 70/30 and 50/50 read/write, footprint and thread sweeps. Traffic buffers total ~256MiB plus a 64MiB read probe; batches last ~120ms. Useful throughput counts 8B operations, not bus bytes or store persistence.')
story.append(picture('project2/figures/report_summary.png',510))
para('Figure 2. Working-set latency (left); throughput/intensity and loaded-read-latency tradeoff (right). Medians +/- sample SD.','SmallLocal')
rows=[['Observed random-load regime','Footprint','Median ns/load','Median cycles/load']]
for r in data('project2/data/processed/latency_baselines.csv'):
    rows.append([r['region'],f'{int(float(r["footprint_bytes"]))/2**20:g}MiB',f'{float(r["median_ns"]):.2f}',f'{float(r["median_cycles"]):.2f}'])
table(rows,[225,85,100,100])
section('Interpretation',"The latency table describes observed regimes, not isolated physical-level constants; sequential prefetching can lower latency. Throughput rises from 7.89GiB/s (1 worker) to 13.26 (2) and 13.98 (4), then falls to 12.53 (12). The >=90%-of-maximum knee is 2 workers. Loaded reads rise from ~118 to 154ns; scheduling and E-core use also matter. Little's Law L = lambda W applies to one request population; stream rate times a different probe's latency is only illustrative. Larger numeric footprints slow with more cache misses. AMAT needs per-access probabilities: the chase-only 66/64 instruction-to-load conversion underpredicts the largest case (~43ns vs 110ns), so it is not a validated multilevel model.")
section('Verification','Cycle uniqueness and read/write references passed. All 42 Instruments captures (3 per case) retain traces/XML and leaf-kernel attribution. Events include L1D load-cache/TLB misses, L2 data-TLB misses, cycles and instructions; misses are normalized per 1,000 sampled instructions. INST_SIMD_ALU also counts scalar FP. Explicit 2MiB superpage allocation failed (invalid argument); no 4KiB/huge-page result is fabricated.')
section('Negative case','Reusing 64KiB (~9.12GiB/s) is a misleading DRAM test versus 256MiB (~7.89GiB/s); loop overhead also prevents claiming physical peak bandwidth. Page-offset balancing and 63/64-load controls preserve the cache-conflict and tiny-cycle anomalies without inventing an architectural cause.')
para('Other plots: working_set_latency, throughput_latency, granularity_latency, pattern_rw_granularity, hardware_counters, numeric_cache_correlation, page_locality, page_offset_control, cache_reuse_pitfall, tiny_cycle_unroll (project2/figures/). All 33 supplementary timings and failed page-support evidence are retained.','SmallLocal')
story.append(PageBreak())

para('Project 3 | SSD performance','TitleLocal')
section('Hypothesis','IOPS should plateau and latency rise with concurrency; larger blocks help throughput; buffering may measure RAM.')
section('Method','FIO 3.43/posixaio tests an owned 1GiB disposable file on APPLE SSD AP1024Z (~1TB), Apple Fabric/APFS: 16KiB memory alignment, incompressible buffers, direct=1/F_NOCACHE. No raw device was written; completion without per-I/O fsync does not prove NAND persistence. There are 47 cases x3 shuffled trials (141 performance jobs; 147 directional CSV rows) plus 2 preparation jobs: six block sizes (4-256KiB), sequential/random read/write, required mixes, QD1-256, 2/4/8/12 forked processes and 64/256/1024MiB logical ranges. Main jobs use 1s and byte caps. Plots show medians +/- SD; tails include every trial and min-max.')
rows=[['QD1 pattern','Mean latency (us)','p95 (us)','p99 (us)']]
for r in data('project3/data/processed/zero_queue_baselines.csv'):
    rows.append([f'{r["rw"]}, {int(r["bs"])//1024}KiB',*[f'{float(r[c]):.1f}' for c in ['mean_latency_us','p95_us','p99_us']]])
table(rows,[210,110,95,95])
story.append(picture('project3/figures/report_summary.png',510))
para('Figure 3. Throughput versus total I/O latency, including forked processes (left); all tail trials with median and min-max (right).','SmallLocal')
section('Interpretation','The single-process >=90%-of-maximum knee is QD8 (~55.9k median IOPS). Forked processes reach ~90 in-flight requests yet stay near 53k IOPS as mean latency rises to ~1.71ms. L = IOPS x mean total latency describes the application population, not controller occupancy. Highest individual read rates were 64,952 random IOPS and 3,955MiB/s sequential; no numerical Apple Fabric/PCIe ceiling is inferred. Temperatures were 28-39C; physical APFS LBAs are unknown. Existing-state burst tests do not establish steady state, SLC exhaustion or thermal throttling.')
tails=data('project3/data/processed/tail_counts.csv')
rows=[['Read-only tail run','p50 (us)','p95 (us)','p99 (us)','p99.9 median / max (us)']]
for case in sorted({r['case_id'] for r in tails}):
    z=[r for r in tails if r['case_id']==case]
    rows.append([case,*[f'{statistics.median(float(r[k])/1000 for r in z):.1f}' for k in ['p50_ns','p95_ns','p99_ns']],f'{statistics.median(float(r["p999_ns"])/1000 for r in z):.1f} / {max(float(r["p999_ns"])/1000 for r in z):.1f}'])
table(rows,[150,75,75,75,135])
section('Verification','Separate 64MiB CRC32C write/read validation passed; no I/O errors. Payload writes were 53.375GiB (<104GiB cap). All six read-only tail jobs completed >=123,209 requests (~123 expected beyond p99.9); all four percentiles and counts are retained. Total/completion latency differ; directional percentiles are not averaged. The ~7.37ms p99.9 outlier remains; scheduling/background I/O or device management are plausible, not proven GC.')
section('Negative case','Requested QD32-256 produces only ~16 average in-flight requests, so requested depth is misleading. Warmed buffered reads strongly inflate apparent SSD IOPS; the direct-I/O comparison exposes the page-cache effect.')
para('Complete plots, FIO configs, JSON+ histograms, temperatures and write ledger: project3/.','SmallLocal')

def main():
    doc=SimpleDocTemplate(str(ROOT/'REPORT.pdf'),pagesize=(612,792),rightMargin=42,leftMargin=42,topMargin=33,bottomMargin=44,title='ECSE 4320/6320 - Three class projects',author='')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print('Generated',ROOT/'REPORT.pdf')
if __name__=='__main__':main()
