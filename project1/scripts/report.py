"""Create the concise three-project report from retained processed measurements."""
from pathlib import Path
import csv,json,statistics,re,html
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.colors import HexColor,black
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader
ROOT=Path(__file__).resolve().parents[2]
import subprocess,sys
plot_python=ROOT/'.venv/bin/python'
subprocess.run([str(plot_python) if plot_python.exists() else sys.executable,str(Path(__file__).with_name('report_figures.py'))],check=True)
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleLocal',fontName='Helvetica-Bold',fontSize=19,leading=23,textColor=HexColor('#17384c'),spaceAfter=8,keepWithNext=True))
styles.add(ParagraphStyle(name='BodyLocal',fontName='Helvetica',fontSize=9.1,leading=12,spaceAfter=6))
styles.add(ParagraphStyle(name='BulletLocal',parent=styles['BodyLocal'],leftIndent=12,bulletIndent=0,spaceAfter=4))
styles.add(ParagraphStyle(name='SmallLocal',fontName='Helvetica',fontSize=7.4,leading=9.4,textColor=HexColor('#465865'),spaceAfter=5))
styles.add(ParagraphStyle(name='TableLocal',parent=styles['SmallLocal'],textColor=black))
styles.add(ParagraphStyle(name='SubLocal',fontName='Helvetica-Bold',fontSize=10.5,leading=13,spaceBefore=5,spaceAfter=4,textColor=HexColor('#17384c'),keepWithNext=True))
story=[]
markdown=['# ECSE 4320/6320 - Class projects']
def md_text(text):
    text=re.sub(r'</?b>','**',str(text))
    return html.unescape(re.sub(r'</?font\b[^>]*>','',text))
def para(text,style='BodyLocal'):
    story.append(Paragraph(text,styles[style]))
    prefix='## ' if style=='TitleLocal' else '### ' if style=='SubLocal' else ''
    markdown.append(prefix+md_text(text))
def section(title,text):para(title,'SubLocal');para(text)
def bullet(text):
    story.append(Paragraph(text,styles['BulletLocal'],bulletText='\u2022'))
    markdown.append('- '+md_text(text))
def figure(project,caption):
    story.append(KeepTogether([picture(f'project{project}/figures/report_summary.png',510),Paragraph(caption,styles['SmallLocal'])]))
    markdown.extend([f'![Project {project} overview](project{project}/figures/report_summary.png)',md_text(caption)])
def data(path):
    with (ROOT/path).open() as f:return list(csv.DictReader(f))
def variability(rows,column,scale=1,expected=5):
    values=[float(r[column])/scale for r in rows]
    assert len(values)==expected,(column,len(values),expected)
    return f'{statistics.median(values):.3g} +/- {statistics.stdev(values):.3g}'
def js(path):return json.loads((ROOT/path).read_text())
def table(rows,widths):
    cells=[[Paragraph(str(c),styles['TableLocal']) for c in row] for row in rows]
    t=Table(cells,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.5,black),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),3)]));story.extend([t,Spacer(1,5)])
    lines=['| '+' | '.join(md_text(c).replace('|','\\|') for c in row)+' |' for row in rows]
    lines.insert(1,'| '+' | '.join('---' for _ in rows[0])+' |')
    markdown.append('\n'.join(lines))
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
para('Method','SubLocal')
for text in ['<b>AXPY:</b> y[i] = a*x[i] + y[i].', '<b>Elementwise multiply:</b> z[i] = x[i]*y[i].', '<b>Three-point stencil:</b> z[i] = a*x[i-1] + b*x[i] + c*x[i+1].']:
    bullet(text)
para('Each kernel was tested with scalar, auto and native builds: -O3 -ffp-contract=off; scalar disables loop/SLP vectors, native adds -mcpu=native; no fast-math/LTO. Initialized 128B-aligned arrays, warmup and reference checks precede ~30ms batches. Five shuffled trials; summary curves show medians and tables report variability; cycles come from real rusage deltas.')
figure(1,'Figure 1. Native float32 speedup over scalar versus active array footprint; higher values mean greater SIMD benefit. Gray lines mark P-core L1D (128KiB) and shared L2 (16MiB). Points show five-trial medians; Table 1 gives the corresponding variability.')
para('<b>Table 1.</b> Figure 1 speedups: median +/- sample standard deviation (five trials, denominator n-1). Larger SD means more trial-to-trial variation; these are not confidence intervals. Active footprint is 8N bytes for AXPY/stencil and 12N bytes for multiply.','SmallLocal')
p1=[r for r in data('project1/data/processed/measurements.csv') if r['build']=='native' and r['dtype']=='f32' and 'baseline_locality_dtype' in r['suites']]
rows=[['Elements (N)','AXPY speedup','Multiply speedup','Stencil speedup']]
for n in sorted({int(r['n']) for r in p1}):
    rows.append([f'{n:,}',*[variability([r for r in p1 if int(r['n'])==n and r['kernel']==kernel],'speedup') for kernel in ['axpy','mul','stencil']]])
table(rows,[105,135,135,135])
rows=[['Native / scalar median speedup','f32, N=1,024','f32, N=16,777,216','f64, N=16,777,216']]
k=data('project1/data/processed/key_comparisons.csv')
for kernel in ['axpy','mul','stencil']:
    def speed(dtype,n):return float(next(r for r in k if r['kernel']==kernel and r['dtype']==dtype and int(r['n'])==n)['speedup'])
    rows.append([kernel,f'{speed("f32",1024):.2f}x',f'{speed("f32",16777216):.2f}x',f'{speed("f64",16777216):.2f}x'])
table(rows,[175,105,120,110])
para('Interpretation','SubLocal')
for text in ['<b>AXPY:</b> Gains shrink as data movement grows; shifted addresses cost about 10-47% in tested cases.', '<b>Elementwise multiply:</b> Gains shrink with size; stride 1 to 8 cuts useful bandwidth from 106 to 10.2GiB/s and native speedup to ~0.99x.', '<b>Three-point stencil:</b> Float32 speedup stays near 3.3x, consistent with reuse of neighboring values.']:
    bullet(text)
para('NEON lane counts (4 float32 / 2 float64) do not guarantee equal speedup. N/N+1 effects include scalar tails and loop overhead.')
para(f'STREAM Copy measured {a1["copy_bandwidth_GB_s"]:.1f}GB/s; 16 verified register FMAs estimate {a1["empirical_compute_ceiling_gflops"]:.1f}GFLOP/s. Float32 arithmetic intensities are AXPY 2/12, multiply 1/12, stencil 5/8 FLOP/B. Roofline measured values are 20.0, 9.1 and 49.0GFLOP/s: memory traffic constrains low-intensity loops. AXPY exceeds the Copy-derived line by ~12%, so it is an approximate traffic-dependent reference.')
section('Verification','All 1,200 primary rows and 324 boundary checks passed. Compiler remarks/disassembly verify vector width and scalar tails. The compute-ceiling loop contains the expected 16 vector FMAs.')
section('Negative case','Ordinary dot uses SIMD products but serial additions (~1.00-1.09x); 30 volatile-accumulator controls verify an explicit non-vectorized loop. The incorrect 9-FMA pilot was rejected. Two migrated rows remain included.')
para('Additional required figures: baseline_speedup, baseline_throughput, cycles_per_element, alignment_tail, stride, data_type, roofline (project1/figures/). Detailed numbers and negative-control evidence remain with the project.','SmallLocal')
story.append(Spacer(1,12))

para('Project 2 | Cache and memory','TitleLocal')
section('Hypothesis','Random dependent loads should slow beyond local caches; concurrency should initially increase bandwidth, then loaded latency. Page spreading should increase translation pressure, with cache conflicts as a confounder.')
para('Method','SubLocal')
bullet('<b>Dependent-load chase:</b> Prefaulted, warmed seeded chains sweep footprints, sequential/random patterns and 64/256/1024B spacings.')
bullet('<b>Read/write traffic and probe:</b> Test 100/0, 0/100, 70/30 and 50/50 mixes and thread counts, using ~256MiB traffic buffers plus a 64MiB read probe.')
bullet('<b>Numeric and page-locality controls:</b> Compare footprint-related cache misses, page spreading, balanced page offsets and tiny-cycle unrolling.')
para('Native C equivalents of MLC use real cycle counters, ~120ms batches and five trials: 355 primary rows (71 cases x5). Useful throughput counts 8B operations, not bus bytes or store persistence. Pages are 16KiB; cache lines are 128B. P-core L1D/shared L2 are 128KiB/16MiB; E-core equivalents are 64KiB/4MiB. No isolated L3 is exposed.')
figure(2,'Figure 2. Left: dependent-load latency versus address footprint; higher latency marks slower observed memory regimes. Right: useful throughput versus loaded-read latency; labels give traffic-thread counts. Points show five-trial medians; Tables 2-3 report the variability of both panels and both axes.')
p2=data('project2/data/processed/measurements.csv')
chase=[r for r in p2 if r['mode']=='chase' and 'baseline_workingset' in r['suites']]
para('<b>Table 2.</b> Figure 2 left: latency in ns/load, median +/- sample SD (five trials).','SmallLocal')
rows=[['Footprint (MiB)','Sequential ns/load','Random ns/load']]
for size in sorted({int(r['bytes']) for r in chase}):
    rows.append([f'{size/2**20:g}',*[variability([r for r in chase if int(r['bytes'])==size and r['pattern']==pattern],'latency_ns') for pattern in ['sequential','random']]])
table(rows,[110,200,200])
traffic=[r for r in p2 if r['mode']=='traffic' and 'intensity' in r['suites']]
para('<b>Table 3.</b> Figure 2 right: median +/- sample SD (five trials). Larger SD means more variation, not a confidence interval.','SmallLocal')
rows=[['Traffic threads','Loaded probe (ns/load)','Useful throughput (GiB/s)']]
for threads in sorted({int(float(r['threads'])) for r in traffic}):
    z=[r for r in traffic if int(float(r['threads']))==threads]
    rows.append([threads,variability(z,'probe_latency_ns'),variability(z,'useful_gib_per_s')])
table(rows,[110,200,200])
rows=[['Observed random-load regime','Footprint','Median ns/load','Median cycles/load']]
for r in data('project2/data/processed/latency_baselines.csv'):
    rows.append([r['region'],f'{int(float(r["footprint_bytes"]))/2**20:g}MiB',f'{float(r["median_ns"]):.2f}',f'{float(r["median_cycles"]):.2f}'])
table(rows,[225,85,100,100])
para('Interpretation','SubLocal')
bullet('<b>Dependent-load chase:</b> The table describes observed regimes, not isolated physical-level constants; sequential prefetching can lower latency.')
bullet('<b>Read/write traffic and probe:</b> Throughput rises from 7.89GiB/s (1 worker) to 13.26 (2) and 13.98 (4), then falls to 12.53 (12). The >=90%-of-maximum knee is 2 workers. Loaded reads rise from ~118 to 154ns; scheduling and E-core use also matter.')
matrix=[r for r in p2 if r['mode']=='traffic' and 'pattern_granularity_rw' in r['suites']]
def memory_median(pattern,spacing,readpct,column):
    return statistics.median(float(r[column]) for r in matrix if r['pattern']==pattern and int(r['spacing'])==spacing and int(float(r['read_percent']))==readpct)
sequential=[memory_median('sequential',s,100,'useful_gib_per_s') for s in [64,256,1024]]
random=[memory_median('random',s,100,'useful_gib_per_s') for s in [64,256,1024]]
bullet(f'<b>Pattern and granularity:</b> With one worker and ~256MiB traffic, sequential read throughput is {sequential[0]:.2f}, {sequential[1]:.2f} and {sequential[2]:.2f}GiB/s at 64/256/1024B spacing; random reads stay near {min(random):.2f}-{max(random):.2f}GiB/s. Wider spacing reduces useful data per fetched line, while random access weakens prefetching; index/loop overhead also contributes.')
mix_bandwidth=[memory_median('sequential',64,p,'useful_gib_per_s') for p in [100,70,50,0]]
mix_probe=[memory_median('sequential',64,p,'probe_latency_ns') for p in [100,70,50,0]]
bullet(f'<b>Read/write mix:</b> At 64B sequential spacing, 100/0, 70/30, 50/50 and 0/100 read/write mixes give {", ".join(f"{x:.2f}" for x in mix_bandwidth)}GiB/s; loaded-read probes are {", ".join(f"{x:.0f}" for x in mix_probe)}ns/load. Pure reads perform best here; stores can add ownership/writeback traffic, but mixed results are not monotonic and do not measure durable-write latency.')
bullet('<b>Numeric and page-locality controls:</b> Larger numeric footprints slow with more cache misses. Page-offset balancing helps distinguish translation pressure from cache conflicts.')
para("Little's Law L = lambda W applies to one request population; stream rate times a different probe's latency is only illustrative. AMAT needs per-access probabilities: the chase-only 66/64 instruction-to-load conversion underpredicts the largest case (~43ns vs 110ns), so it is not a validated multilevel model.")
section('Verification','Cycle uniqueness and read/write references passed. All 42 Instruments captures (3 per case) retain traces/XML and leaf-kernel attribution. Events include L1D load-cache/TLB misses, L2 data-TLB misses, cycles and instructions; misses are normalized per 1,000 sampled instructions. INST_SIMD_ALU also counts scalar FP. Explicit 2MiB superpage allocation failed (invalid argument); no 4KiB/huge-page result is fabricated.')
section('Negative case','Reusing 64KiB (~9.12GiB/s) is a misleading DRAM test versus 256MiB (~7.89GiB/s); loop overhead also prevents claiming physical peak bandwidth. Page-offset balancing and 63/64-load controls preserve the cache-conflict and tiny-cycle anomalies without inventing an architectural cause.')
para('Other plots: working_set_latency, throughput_latency, granularity_latency, pattern_rw_granularity, hardware_counters, numeric_cache_correlation, page_locality, page_offset_control, cache_reuse_pitfall, tiny_cycle_unroll (project2/figures/). All 33 supplementary timings and failed page-support evidence are retained.','SmallLocal')
story.append(Spacer(1,12))

para('Project 3 | SSD performance','TitleLocal')
section('Hypothesis','IOPS should plateau and latency rise with concurrency; larger blocks help throughput; buffering may measure RAM.')
para('Method','SubLocal')
bullet('<b>Pattern, block size and mix:</b> Test sequential/random reads and writes, six block sizes (4-256KiB) and required read/write mixes; QD1 supplies the baseline.')
bullet('<b>Queue depth and parallelism:</b> Sweep QD1-256 and 2/4/8/12 forked processes to compare throughput and total I/O latency.')
bullet('<b>Tail latency and range/cache controls:</b> Record p50/p95/p99/p99.9 and request counts near and below the knee; compare 64/256/1024MiB logical ranges and buffered/direct I/O.')
para('FIO 3.43/posixaio tests an owned 1GiB disposable file on APPLE SSD AP1024Z (~1TB), Apple Fabric/APFS: 16KiB memory alignment, incompressible buffers, direct=1/F_NOCACHE. No raw device was written; completion without per-I/O fsync does not prove NAND persistence. There are 47 cases x3 shuffled trials (141 performance jobs; 147 directional CSV rows) plus 2 preparation jobs. Main jobs use 1s and byte caps.')
rows=[['QD1 pattern','Mean latency (us)','p95 (us)','p99 (us)']]
for r in data('project3/data/processed/zero_queue_baselines.csv'):
    rows.append([f'{r["rw"]}, {int(r["bs"])//1024}KiB',*[f'{float(r[c]):.1f}' for c in ['mean_latency_us','p95_us','p99_us']]])
table(rows,[210,110,95,95])
figure(3,'Figure 3. Left: random 4KiB throughput versus mean total latency, with queue-depth and process-count sweeps. Right: tail percentiles at QD4/QD8. Points show three-trial medians; Table 4 gives throughput/latency SD and Table 5 gives tail ranges, preserving variability without error bars.')
para('<b>Table 4.</b> Figure 3 left: median +/- sample SD (three trials). The QD sweep uses one process; the process-count sweep fixes QD8 per process.','SmallLocal')
rows=[['Configuration','Throughput (thousand IOPS)','Mean total latency (ms)']]
for source,key,label in [('queue_curve.csv','requested_qd','QD'),('parallelism.csv','numjobs','Processes')]:
    for r in data(f'project3/data/processed/{source}'):
        rows.append([f'{label} {int(float(r[key]))}',f'{float(r["iops_median"])/1000:.3g} +/- {float(r["iops_std"])/1000:.3g}',f'{float(r["combined_mean_latency_ns_median"])/1e6:.3g} +/- {float(r["combined_mean_latency_ns_std"])/1e6:.3g}'])
table(rows,[110,200,200])
para('Interpretation','SubLocal')
p3=data('project3/data/processed/measurements.csv')
def ssd_median(suite,column,**conditions):
    unique={}
    for r in p3:
        if suite in r['suites'] and all(r[k]==str(v) if isinstance(v,str) else float(r[k])==v for k,v in conditions.items()):
            unique[(r['case_id'],r['trial'])]=float(r[column])
    return statistics.median(unique.values())
block={rw:[ssd_median('block_pattern','bandwidth_mib_s',rw=rw,bs=size) for size in [4096,262144]] for rw in ['read','randread','write','randwrite']}
read_latency=[ssd_median('block_pattern','combined_mean_latency_ns',rw='randread',bs=size)/1000 for size in [4096,262144]]
bullet(f'<b>Pattern and block size:</b> At QD1, 4 to 256KiB raises sequential-read throughput from {block["read"][0]:.0f} to {block["read"][1]:.0f}MiB/s and random reads from {block["randread"][0]:.1f} to {block["randread"][1]:.0f}MiB/s. The sequential/random gap narrows as larger transfers amortize request overhead; random-read mean latency rises from {read_latency[0]:.1f} to {read_latency[1]:.1f}us, so higher MiB/s does not imply lower latency or higher IOPS. Sequential/random writes rise from {block["write"][0]:.0f}/{block["randwrite"][0]:.1f} to {block["write"][1]:.0f}/{block["randwrite"][1]:.0f}MiB/s; these are burst completion rates, not durable NAND-write rates.')
mix_iops=[ssd_median('rw_mix','iops',read_percent=p)/1000 for p in [0,50,70,100]]
mix_latency=[ssd_median('rw_mix','combined_mean_latency_ns',read_percent=p)/1000 for p in [0,50,70,100]]
bullet(f'<b>Read/write mix:</b> Random 4KiB, QD16, with 0/100, 50/50, 70/30 and 100/0 read/write mixes yields {", ".join(f"{x:.1f}" for x in mix_iops)} thousand IOPS and {", ".join(f"{x:.0f}" for x in mix_latency)}us mean total latency. More reads help this measured device state; the trend is not a universal SSD rule. Highest individual read rates were 64,952 random IOPS and 3,955MiB/s sequential; no numerical Apple Fabric/PCIe ceiling is inferred.')
bullet('<b>Queue depth and parallelism:</b> The single-process >=90%-of-maximum knee is QD8 (~55.9k median IOPS). Forked processes reach ~90 in-flight requests yet stay near 53k IOPS as mean latency rises to ~1.71ms. L = IOPS x mean total latency describes the application population, not controller occupancy.')
bullet('<b>Tail latency and range/cache controls:</b> Table 5 retains the median and full trial range of every tail percentile; warmed buffered reads can inflate apparent SSD performance. Logical file ranges do not reveal physical APFS LBAs.')
para('Temperatures were 28-39C. Existing-state burst tests do not establish steady state, SLC exhaustion or thermal throttling.')
tails=data('project3/data/processed/tail_counts.csv')
para('<b>Table 5.</b> Figure 3 right: median [minimum, maximum] in us, across three trials per configuration. Ranges describe observed trials, not confidence intervals.','SmallLocal')
rows=[['Read-only tail run','p50 (us)','p95 (us)','p99 (us)','p99.9 (us)']]
for case in sorted({r['case_id'] for r in tails}):
    z=[r for r in tails if r['case_id']==case]
    assert len(z)==3
    cells=[]
    for column in ['p50_ns','p95_ns','p99_ns','p999_ns']:
        values=[float(r[column])/1000 for r in z]
        cells.append(f'{statistics.median(values):.1f}<br/>[{min(values):.1f}, {max(values):.1f}]')
    rows.append([case,*cells])
table(rows,[110,100,100,100,100])
section('Verification','Separate 64MiB CRC32C write/read validation passed; no I/O errors. Payload writes were 53.375GiB (<104GiB cap). All six read-only tail jobs completed >=123,209 requests (~123 expected beyond p99.9); all four percentiles and counts are retained. Total/completion latency differ; directional percentiles are not averaged. The ~7.37ms p99.9 outlier remains; scheduling/background I/O or device management are plausible, not proven GC.')
section('Negative case','Requested QD32-256 produces only ~16 average in-flight requests, so requested depth is misleading. Warmed buffered reads strongly inflate apparent SSD IOPS; the direct-I/O comparison exposes the page-cache effect.')
para('Complete plots, FIO configs, JSON+ histograms, temperatures and write ledger: project3/.','SmallLocal')

def main():
    doc=SimpleDocTemplate(str(ROOT/'REPORT.pdf'),pagesize=(612,792),rightMargin=42,leftMargin=42,topMargin=33,bottomMargin=44,title='ECSE 4320/6320 - Three class projects',author='')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    (ROOT/'REPORT.md').write_text('\n\n'.join(markdown)+'\n')
    print('Generated',ROOT/'REPORT.pdf')
if __name__=='__main__':main()
