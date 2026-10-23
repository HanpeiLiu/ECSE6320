#include "kernels.h"
/* Separate translation unit, no LTO: repeated calls cannot be deleted by the driver. */
#define DEFINE(T,S) \
__attribute__((noinline)) void axpy_##S(T *restrict y,const T *restrict x,size_t n,size_t stride,T a) { \
    if(stride==1) {for(size_t i=0;i<n;i++) y[i]=a*x[i]+y[i];} \
    else {for(size_t i=0;i<n;i++) y[i*stride]=a*x[i*stride]+y[i*stride];} \
} \
__attribute__((noinline)) void mul_##S(T *restrict z,const T *restrict x,const T *restrict y,size_t n,size_t stride) { \
    if(stride==1) {for(size_t i=0;i<n;i++) z[i]=x[i]*y[i];} \
    else {for(size_t i=0;i<n;i++) z[i*stride]=x[i*stride]*y[i*stride];} \
} \
__attribute__((noinline)) void stencil_##S(T *restrict z,const T *restrict x,size_t n,size_t stride,T a,T b,T c) { \
    if(stride==1) {for(size_t i=1;i+1<n;i++) z[i]=a*x[i-1]+b*x[i]+c*x[i+1];} \
    else {for(size_t i=1;i+1<n;i++) z[i*stride]=a*x[(i-1)*stride]+b*x[i*stride]+c*x[(i+1)*stride];} \
} \
__attribute__((noinline)) T dot_##S(const T *restrict x,const T *restrict y,size_t n,size_t stride) { \
    T s=0; for(size_t i=0;i<n;i++) s+=x[i*stride]*y[i*stride]; return s; \
}
DEFINE(float,f32)
DEFINE(double,f64)
