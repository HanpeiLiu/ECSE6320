#include "kernels.h"
#include "../../shared/measurement.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#ifndef BUILD_NAME
#define BUILD_NAME "unknown"
#endif
static volatile double sink;

#define DRIVER(T,S) \
static int run_##S(const char *kernel,size_t n,size_t stride,size_t offset,double target) { \
    size_t count=n*stride+offset+32; void *bx=0,*by=0,*bz=0; \
    if(posix_memalign(&bx,128,count*sizeof(T)) || posix_memalign(&by,128,count*sizeof(T)) || posix_memalign(&bz,128,count*sizeof(T)))return 2; \
    T *x=(T*)bx+offset,*y=(T*)by+offset,*z=(T*)bz+offset; \
    for(size_t i=0;i<n*stride+8;i++){x[i]=(T)((int)(i%97)-48)/(T)64;y[i]=(T)((int)(i%71)-35)/(T)64;z[i]=0;} \
    int k=!strcmp(kernel,"axpy")?0:!strcmp(kernel,"mul")?1:!strcmp(kernel,"stencil")?2:!strcmp(kernel,"dot")?3:-1; \
    if(k<0)return 3; T a=(T)0.0009765625,b=(T)0.5,c=(T)0.25; T dotresult=0; \
    if(k==0)axpy_##S(y,x,n,stride,a); \
    if(k==1)mul_##S(z,x,y,n,stride); \
    if(k==2)stencil_##S(z,x,n,stride,a,b,c); \
    if(k==3)dotresult=dot_##S(x,y,n,stride); \
    long double maxerr=0,refdot=0; \
    for(size_t i=0;i<n;i++){size_t j=i*stride; \
        long double xv=(long double)x[j],yv=(long double)((T)((int)(j%71)-35)/(T)64),ref=0,got=0; \
        if(k==0){ref=(T)((T)(a*x[j])+(T)yv);got=y[j];} \
        if(k==1){ref=(T)(x[j]*y[j]);got=z[j];} \
        if(k==2 && i>0 && i+1<n){ref=(T)((T)((T)(a*x[j-stride])+(T)(b*x[j]))+(T)(c*x[j+stride]));got=z[j];} \
        if(k==3)refdot+=xv*yv; \
        long double err=fabsl(got-ref);if(err>maxerr)maxerr=err; \
    } \
    if(k==3)maxerr=fabsl((long double)dotresult-refdot); \
    long double tolerance=sizeof(T)==4?1e-5L:1e-11L; \
    if(maxerr>tolerance*(1+fabsl(refdot))){fprintf(stderr,"correctness failed: %Lg\n",maxerr);return 4;} \
    uint64_t reps=1,t=0; \
    do{uint64_t start=wall_ns();for(uint64_t r=0;r<reps;r++){ \
        if(k==0)axpy_##S(y,x,n,stride,a);else if(k==1)mul_##S(z,x,y,n,stride); \
        else if(k==2)stencil_##S(z,x,n,stride,a,b,c);else sink=dot_##S(x,y,n,stride); \
    }t=wall_ns()-start;if(t<2000000ULL)reps*=2;}while(t<2000000ULL && reps<(1ULL<<27)); \
    double estimate=(double)t/(double)reps; \
    reps=(uint64_t)ceil(target*1e9/estimate);if(reps<1)reps=1;if(reps>100000000ULL)reps=100000000ULL; \
    /* Reset AXPY output after calibration; all initialization stays outside timing. */ \
    for(size_t i=0;i<n*stride;i++)y[i]=(T)((int)(i%71)-35)/(T)64; \
    os_log_t log=measurement_log();os_signpost_id_t sid=os_signpost_id_generate(log); \
    os_signpost_interval_begin(log,sid,"Measurement"); \
    cpu_count before=cpu_snapshot();uint64_t cpu0=thread_ns(),t0=wall_ns(); \
    for(uint64_t r=0;r<reps;r++){ \
        if(k==0)axpy_##S(y,x,n,stride,a);else if(k==1)mul_##S(z,x,y,n,stride); \
        else if(k==2)stencil_##S(z,x,n,stride,a,b,c);else sink=dot_##S(x,y,n,stride); \
    } \
    uint64_t elapsed=wall_ns()-t0,cpu_elapsed=thread_ns()-cpu0;cpu_count after=cpu_snapshot(); \
    os_signpost_interval_end(log,sid,"Measurement"); \
    long double checksum=0;for(size_t i=0;i<n;i++)checksum+=(k==0?y[i*stride]:k==3?x[i*stride]:z[i*stride]);sink=(double)checksum; \
    size_t elems=k==2?n-2:n;unsigned arrays=k==1?3:2;double seconds=elapsed*1e-9; \
    double bytes=(double)elems*sizeof(T)*(k==2?2:k==3?2:3); \
    double flops=(double)elems*(k==0?2:k==1?1:k==2?5:2); \
    uint64_t cycles=after.cycles-before.cycles,instructions=after.instructions-before.instructions; \
    printf("{\"build\":\"%s\",\"kernel\":\"%s\",\"dtype\":\"%s\",\"n\":%zu,\"stride\":%zu,\"offset_elements\":%zu,\"address_mod_128\":%zu,\"working_set_bytes\":%zu,\"iterations\":%llu,\"elements_per_iteration\":%zu,\"elapsed_ns\":%llu,\"thread_cpu_ns\":%llu,\"cycles_available\":%d,\"cycles\":%llu,\"instructions\":%llu,\"pcycles_available\":%d,\"pcycles\":%llu,\"cycles_per_element\":%.9g,\"gflops\":%.9g,\"gib_per_s\":%.9g,\"checksum\":%.12Lg,\"max_reference_error\":%.12Lg,\"correctness\":true,\"pid\":%d}\n", \
       BUILD_NAME,kernel,#S,n,stride,offset,(size_t)((uintptr_t)x%128),arrays*((n-1)*stride+1)*sizeof(T), \
       (unsigned long long)reps,elems,(unsigned long long)elapsed,(unsigned long long)cpu_elapsed, \
       before.available&&after.available,(unsigned long long)cycles,(unsigned long long)instructions, \
       before.performance_available&&after.performance_available,(unsigned long long)(after.pcycles-before.pcycles), \
       (double)cycles/(reps*(double)elems),flops*reps/seconds/1e9,bytes*reps/seconds/1073741824.,checksum,maxerr,getpid()); \
    free(bx);free(by);free(bz);return 0; \
}
DRIVER(float,f32)
DRIVER(double,f64)
int main(int argc,char **argv){
    if(argc!=7){fprintf(stderr,"usage: bench kernel f32|f64 n stride offset target_seconds\n");return 1;}
    request_performance_qos();size_t n=strtoull(argv[3],0,10),stride=strtoull(argv[4],0,10),offset=strtoull(argv[5],0,10);
    if(n<3||!stride||stride>64||offset>128||n>100000000)return 1;
    return !strcmp(argv[2],"f32")?run_f32(argv[1],n,stride,offset,atof(argv[6])):run_f64(argv[1],n,stride,offset,atof(argv[6]));
}
