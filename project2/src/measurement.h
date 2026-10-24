#ifndef ECSE_MEASUREMENT_H
#define ECSE_MEASUREMENT_H
#include <time.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/resource.h>
#include <libproc.h>
#include <pthread.h>
#include <pthread/qos.h>
#include <os/log.h>
#include <os/signpost.h>

static uint64_t wall_ns(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC_RAW, &t);
    return (uint64_t)t.tv_sec*1000000000ULL+t.tv_nsec;
}
static uint64_t thread_ns(void) {
    struct timespec t; clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t);
    return (uint64_t)t.tv_sec*1000000000ULL+t.tv_nsec;
}
typedef struct {
    uint64_t cycles, instructions, pcycles, pinstructions;
    int available, performance_available;
} cpu_count;
static cpu_count cpu_snapshot(void) {
    cpu_count c={0}; struct rusage_info_v6 r; memset(&r,0,sizeof r);
    if (proc_pid_rusage(getpid(),RUSAGE_INFO_V6,(rusage_info_t*)&r)==0) {
        c.cycles=r.ri_cycles; c.instructions=r.ri_instructions;
        c.pcycles=r.ri_pcycles; c.pinstructions=r.ri_pinstructions;
        c.available=1; c.performance_available=1;
    } else {
        struct rusage_info_v4 q; memset(&q,0,sizeof q);
        if(proc_pid_rusage(getpid(),RUSAGE_INFO_V4,(rusage_info_t*)&q)==0) {
            c.cycles=q.ri_cycles; c.instructions=q.ri_instructions; c.available=1;
        }
    }
    return c;
}
static uint64_t rng_next(uint64_t *s) {
    uint64_t x=*s; x^=x>>12; x^=x<<25; x^=x>>27; *s=x;
    return x*2685821657736338717ULL;
}
static void request_performance_qos(void) {
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INITIATED,0);
}
static os_log_t measurement_log(void) {
    return os_log_create("edu.rpi.ecse6320","benchmark");
}
#endif
