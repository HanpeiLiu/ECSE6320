#include <arm_neon.h>
#include <stdio.h>
#include <stdlib.h>
#include "measurement.h"
/* Independent register-resident FMA chains: an empirical compute ceiling estimate. */
static volatile float sink;
int main(int argc,char **argv){
    uint64_t n=argc>1?strtoull(argv[1],0,10):50000000ULL;request_performance_qos();
    float32x4_t a[16];for(int i=0;i<16;i++)a[i]=vdupq_n_f32((float)i/17);
    /* Runtime operands avoid constant folding of additions below an accumulator's ULP. */
    float32x4_t b=vdupq_n_f32(argc>2?strtof(argv[2],0):0.5f);
    float32x4_t c=vdupq_n_f32(argc>3?strtof(argv[3],0):0.0002f);
    cpu_count cb=cpu_snapshot();uint64_t cpu=thread_ns(),start=wall_ns();
    for(uint64_t k=0;k<n;k++){
        #pragma unroll
        for(int j=0;j<16;j++)a[j]=vfmaq_f32(a[j],b,c);
    }
    uint64_t ns=wall_ns()-start,cns=thread_ns()-cpu;cpu_count ca=cpu_snapshot();
    for(int i=0;i<16;i++)sink+=vaddvq_f32(a[i]);
    printf("{\"iterations\":%llu,\"elapsed_ns\":%llu,\"thread_cpu_ns\":%llu,\"flops\":%.0f,\"gflops\":%.9g,\"cycles\":%llu,\"instructions\":%llu,\"cycles_available\":%d,\"estimated_flops_per_cycle\":%.9g,\"pcycles\":%llu}\n",(unsigned long long)n,(unsigned long long)ns,(unsigned long long)cns,(double)n*128.,(double)n*128./ns,(unsigned long long)(ca.cycles-cb.cycles),(unsigned long long)(ca.instructions-cb.instructions),cb.available&&ca.available,(double)n*128./(ca.cycles-cb.cycles),(unsigned long long)(ca.pcycles-cb.pcycles));
}
