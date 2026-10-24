/* Deliberate negative control: observable volatile accumulator prevents SIMD reduction.
   This changes semantics/cost; it is not an optimization recommendation. */
#include "measurement.h"
#include <stdio.h>
#include <stdlib.h>
#ifndef BUILD_NAME
#define BUILD_NAME "unknown"
#endif
__attribute__((noinline)) float observable_dot(const float *restrict x,const float *restrict y,size_t n) {
    volatile float sum=0;
    for(size_t i=0;i<n;i++)sum=sum+x[i]*y[i];
    return sum;
}
static volatile float sink;
int main(int argc,char **argv) {
    size_t n=argc>1?strtoull(argv[1],0,10):1024;
    if(!n || n>16777216)return 2;
    float *x=malloc(n*sizeof(float)),*y=malloc(n*sizeof(float));if(!x||!y)return 3;
    for(size_t i=0;i<n;i++){x[i]=(float)((int)(i%17)-8)/16;y[i]=(float)((int)(i%13)-6)/16;}
    float ref=0;for(size_t i=0;i<n;i++)ref=ref+x[i]*y[i];
    float got=observable_dot(x,y,n);if(got!=ref)return 4;
    request_performance_qos();sink=observable_dot(x,y,n);
    uint64_t t=wall_ns();for(int j=0;j<4;j++)sink=observable_dot(x,y,n);
    uint64_t pilot=wall_ns()-t;size_t reps=(size_t)(30000000.0*4/(pilot?pilot:1));if(reps<1)reps=1;
    cpu_count a=cpu_snapshot();t=wall_ns();for(size_t j=0;j<reps;j++)sink=observable_dot(x,y,n);
    uint64_t elapsed=wall_ns()-t;cpu_count b=cpu_snapshot();
    printf("{\"build\":\"%s\",\"n\":%zu,\"iterations\":%zu,\"elapsed_ns\":%llu,\"ns_per_element\":%.9g,\"cycles_per_element\":%.9g,\"cycles\":%llu,\"correctness\":true,\"reference\":%.9g,\"result\":%.9g}\n",BUILD_NAME,n,reps,(unsigned long long)elapsed,(double)elapsed/(n*reps),(double)(b.cycles-a.cycles)/(n*reps),(unsigned long long)(b.cycles-a.cycles),ref,got);
    free(x);free(y);return 0;
}
