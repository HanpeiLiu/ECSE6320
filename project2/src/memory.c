#include "measurement.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdatomic.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/vm_statistics.h>
static volatile uint64_t sink;
typedef struct {void *base;uintptr_t start;size_t nodes,spacing,bytes;} chain;
static chain make_chain(size_t bytes,size_t spacing,int random,uint64_t seed){
    chain c={0};c.nodes=bytes/spacing;c.spacing=spacing;c.bytes=bytes;
    if(c.nodes<2||spacing<8||posix_memalign(&c.base,16384,bytes))exit(2);
    memset(c.base,0,bytes);
    size_t *order=malloc(c.nodes*sizeof(size_t));if(!order)exit(2);
    for(size_t i=0;i<c.nodes;i++)order[i]=i;
    if(random)for(size_t i=c.nodes-1;i>0;i--){size_t j=rng_next(&seed)%(i+1),v=order[i];order[i]=order[j];order[j]=v;}
    for(size_t i=0;i<c.nodes;i++)*(uintptr_t*)((char*)c.base+order[i]*spacing)=(uintptr_t)((char*)c.base+order[(i+1)%c.nodes]*spacing);
    c.start=(uintptr_t)((char*)c.base+order[0]*spacing);free(order);
    uintptr_t p=c.start;for(size_t i=0;i<c.nodes;i++)p=*(uintptr_t*)p;
    if(p!=c.start){fprintf(stderr,"reference cycle check failed\n");exit(3);}return c;
}
#define L1 p=*(const uintptr_t*)p;
#define L8 L1 L1 L1 L1 L1 L1 L1 L1
#define L64 L8 L8 L8 L8 L8 L8 L8 L8
__attribute__((noinline)) static uintptr_t chase_batch(uintptr_t p,size_t batches){
    for(size_t i=0;i<batches;i++){L64}return p;
}
static int chase(size_t bytes,size_t spacing,int random,double seconds,uint64_t seed){
    chain c=make_chain(bytes,spacing,random,seed);
    uintptr_t p=chase_batch(c.start,(c.nodes+63)/64);size_t batch=1024;
    uint64_t t=wall_ns();p=chase_batch(p,batch);t=wall_ns()-t;
    if(t<1000000)batch*=4;
    cpu_count a=cpu_snapshot();uint64_t cpu=thread_ns(),start=wall_ns(),loads=0;
    os_log_t log=measurement_log();os_signpost_id_t sid=os_signpost_id_generate(log);
    os_signpost_interval_begin(log,sid,"Measurement");
    do{p=chase_batch(p,batch);loads+=batch*64;}while(wall_ns()-start<(uint64_t)(seconds*1e9));
    uint64_t elapsed=wall_ns()-start,cpuns=thread_ns()-cpu;cpu_count b=cpu_snapshot();
    os_signpost_interval_end(log,sid,"Measurement");sink=p;
    printf("{\"mode\":\"chase\",\"bytes\":%zu,\"spacing\":%zu,\"nodes\":%zu,\"pattern\":\"%s\",\"seed\":%llu,\"elapsed_ns\":%llu,\"thread_cpu_ns\":%llu,\"loads\":%llu,\"latency_ns\":%.9g,\"cycles\":%llu,\"instructions\":%llu,\"cycles_available\":%d,\"pcycles_available\":%d,\"pcycles\":%llu,\"cycles_per_load\":%.9g,\"native_page_bytes\":%d,\"active_line_bytes\":%zu,\"correctness\":true,\"pid\":%d}\n",bytes,spacing,c.nodes,random?"random":"sequential",(unsigned long long)seed,(unsigned long long)elapsed,(unsigned long long)cpuns,(unsigned long long)loads,(double)elapsed/loads,(unsigned long long)(b.cycles-a.cycles),(unsigned long long)(b.instructions-a.instructions),a.available&&b.available,a.performance_available&&b.performance_available,(unsigned long long)(b.pcycles-a.pcycles),(double)(b.cycles-a.cycles)/loads,getpagesize(),c.nodes*(spacing<128?spacing:128),getpid());
    free(c.base);return 0;
}
typedef struct {
    volatile uint64_t *data;size_t *order,nodes,stride_words;int pct,random,id;
    _Atomic int *start,*stop,*ready;
    uint64_t ops,reads,writes,elapsed_ns,checksum,max_ops;
} worker;
static void *traffic_worker(void *arg){
    worker *w=arg;request_performance_qos();atomic_fetch_add(w->ready,1);
    while(!atomic_load_explicit(w->start,memory_order_acquire)){}
    size_t cursor=0;uint64_t ops=0,reads=0,writes=0,sum=0;uint64_t t0=wall_ns();
    while(!atomic_load_explicit(w->stop,memory_order_relaxed)&&(!w->max_ops||ops<w->max_ops)){
        for(int j=0;j<256;j++){
            size_t ix=w->random?w->order[cursor]:cursor;
            volatile uint64_t *ptr=w->data+ix*w->stride_words;
            if(ops%100<(unsigned)w->pct){sum+=*ptr;reads++;}else{*ptr=ops+1;writes++;}
            ops++;if(++cursor==w->nodes)cursor=0;
        }
    }
    w->elapsed_ns=wall_ns()-t0;w->ops=ops;w->reads=reads;w->writes=writes;w->checksum=sum;return 0;
}
static int traffic(size_t bytes,size_t spacing,int random,int pct,int threads,double seconds,uint64_t seed,size_t probe_bytes){
    if(threads<1||threads>16||spacing<8||pct<0||pct>100)return 2;
    chain probe=make_chain(probe_bytes,128,1,seed+17);uintptr_t p=chase_batch(probe.start,(probe.nodes+63)/64);
    worker w[16]={0};pthread_t tids[16];_Atomic int start=0,stop=0,ready=0;
    size_t per_nodes=bytes/(spacing*threads),actual=per_nodes*spacing*threads;
    for(int i=0;i<threads;i++){
        w[i]=(worker){.nodes=per_nodes,.stride_words=spacing/8,.pct=pct,.random=random,.id=i,.start=&start,.stop=&stop,.ready=&ready};
        void *data=0;if(posix_memalign(&data,16384,per_nodes*spacing))return 2;memset(data,1,per_nodes*spacing);w[i].data=data;
        if(random){
            w[i].order=malloc(per_nodes*sizeof(size_t));if(!w[i].order)return 2;
            for(size_t j=0;j<per_nodes;j++)w[i].order[j]=j;
            uint64_t s=seed+i+101;for(size_t j=per_nodes-1;j>0;j--){size_t k=rng_next(&s)%(j+1),v=w[i].order[j];w[i].order[j]=w[i].order[k];w[i].order[k]=v;}
        }
        if(pthread_create(&tids[i],0,traffic_worker,&w[i]))return 2;
    }
    while(atomic_load(&ready)<threads){}
    os_log_t log=measurement_log();os_signpost_id_t sid=os_signpost_id_generate(log);os_signpost_interval_begin(log,sid,"Measurement");
    cpu_count ca=cpu_snapshot();uint64_t cpu=thread_ns(),t0=wall_ns(),loads=0;atomic_store_explicit(&start,1,memory_order_release);
    do{p=chase_batch(p,256);loads+=256*64;}while(wall_ns()-t0<(uint64_t)(seconds*1e9));
    atomic_store_explicit(&stop,1,memory_order_release);uint64_t elapsed=wall_ns()-t0,cpuns=thread_ns()-cpu;cpu_count cb=cpu_snapshot();
    os_signpost_interval_end(log,sid,"Measurement");
    uint64_t ops=0,reads=0,writes=0,checksum=0,worker_min=UINT64_MAX,worker_max=0;
    for(int i=0;i<threads;i++){
        pthread_join(tids[i],0);ops+=w[i].ops;reads+=w[i].reads;writes+=w[i].writes;checksum+=w[i].checksum;
        if(w[i].elapsed_ns<worker_min)worker_min=w[i].elapsed_ns;if(w[i].elapsed_ns>worker_max)worker_max=w[i].elapsed_ns;
        free((void*)w[i].data);free(w[i].order);
    }
    sink=checksum^p;
    printf("{\"mode\":\"traffic\",\"bytes\":%zu,\"requested_bytes\":%zu,\"spacing\":%zu,\"pattern\":\"%s\",\"read_percent\":%d,\"threads\":%d,\"probe_bytes\":%zu,\"elapsed_ns\":%llu,\"probe_thread_cpu_ns\":%llu,\"probe_loads\":%llu,\"probe_latency_ns\":%.9g,\"traffic_ops\":%llu,\"traffic_reads\":%llu,\"traffic_writes\":%llu,\"useful_gib_per_s\":%.9g,\"worker_min_ns\":%llu,\"worker_max_ns\":%llu,\"index_bytes\":%zu,\"process_cycles\":%llu,\"process_instructions\":%llu,\"cycles_available\":%d,\"pcycles\":%llu,\"checksum\":%llu,\"correctness\":true,\"pid\":%d}\n",actual,bytes,spacing,random?"random":"sequential",pct,threads,probe_bytes,(unsigned long long)elapsed,(unsigned long long)cpuns,(unsigned long long)loads,(double)elapsed/loads,(unsigned long long)ops,(unsigned long long)reads,(unsigned long long)writes,(double)ops*8/elapsed*1e9/1073741824.,(unsigned long long)worker_min,(unsigned long long)worker_max,random?per_nodes*threads*sizeof(size_t):0,(unsigned long long)(cb.cycles-ca.cycles),(unsigned long long)(cb.instructions-ca.instructions),ca.available&&cb.available,(unsigned long long)(cb.pcycles-ca.pcycles),(unsigned long long)checksum,getpid());
    free(probe.base);return 0;
}
static int selftest(void){
    for(int random=0;random<2;random++){
        chain c=make_chain(65536,128,random,6320);uintptr_t p=c.start;
        unsigned char seen[512]={0};for(size_t i=0;i<c.nodes;i++){
            size_t ix=(p-(uintptr_t)c.base)/128;if(ix>=512||seen[ix])return 3;seen[ix]=1;p=*(uintptr_t*)p;
        }if(p!=c.start)return 3;free(c.base);
    }
    /* Deterministic read/write operation schedule has exactly the requested mix. */
    for(int pct=0;pct<=100;pct+=10){unsigned reads=0;for(unsigned i=0;i<1000;i++)reads+=(i%100<(unsigned)pct);if(reads!=(unsigned)pct*10)return 3;}
    for(int random=0;random<2;random++)for(int mix=0;mix<4;mix++){
        int pct=(int[]){0,50,70,100}[mix];uint64_t actual[128]={0},expected[128]={0};size_t order[64];
        for(int i=0;i<64;i++){actual[2*i]=expected[2*i]=i+1;order[i]=63-i;}
        uint64_t expected_sum=0,expected_reads=0;
        for(int pass=0;pass<16;pass++)for(int k=0;k<64;k++){
            int index=random?63-k:k,op=pass*64+k;
            if(op%100<pct){expected_sum+=expected[2*index];expected_reads++;}else expected[2*index]=op+1;
        }
        _Atomic int start=1,stop=0,ready=0;
        worker w={.data=actual,.order=order,.nodes=64,.stride_words=2,.pct=pct,.random=random,
                  .start=&start,.stop=&stop,.ready=&ready,.max_ops=1024};
        traffic_worker(&w);
        if(w.ops!=1024||w.reads!=expected_reads||w.writes!=1024-expected_reads||w.checksum!=expected_sum||memcmp(actual,expected,sizeof actual))return 3;
    }
    puts("{\"selftest\":true,\"cycle_unique_nodes\":true,\"mix_schedule\":true,\"traffic_reference\":true}");return 0;
}
int main(int argc,char **argv){
    request_performance_qos();
    if(argc==2&&!strcmp(argv[1],"selftest"))return selftest();
    if(argc==2&&!strcmp(argv[1],"hugepage")){
        mach_vm_address_t a=0;size_t size=2097152;
        kern_return_t r=mach_vm_allocate(mach_task_self(),&a,size,VM_FLAGS_ANYWHERE|VM_FLAGS_SUPERPAGE_SIZE_2MB);
        printf("{\"native_page_bytes\":%d,\"requested_superpage_bytes\":%zu,\"kern_return\":%d,\"message\":\"%s\",\"allocation_succeeded\":%s}\n",getpagesize(),size,r,mach_error_string(r),r==0?"true":"false");
        if(!r)mach_vm_deallocate(mach_task_self(),a,size);return 0;
    }
    if(argc==7&&!strcmp(argv[1],"chase"))return chase(strtoull(argv[2],0,10),strtoull(argv[3],0,10),!strcmp(argv[4],"random"),atof(argv[5]),strtoull(argv[6],0,10));
    if(argc==10&&!strcmp(argv[1],"traffic"))return traffic(strtoull(argv[2],0,10),strtoull(argv[3],0,10),!strcmp(argv[4],"random"),atoi(argv[5]),atoi(argv[6]),atof(argv[7]),strtoull(argv[8],0,10),strtoull(argv[9],0,10));
    fprintf(stderr,"usage: memory chase bytes spacing random|sequential seconds seed\n or traffic bytes spacing pattern readpct threads seconds seed probe_bytes\n or selftest|hugepage\n");return 1;
}
