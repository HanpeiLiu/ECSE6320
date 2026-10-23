#include <stddef.h>
#define DECL(T,S) \
void axpy_##S(T *restrict y,const T *restrict x,size_t n,size_t stride,T a); \
void mul_##S(T *restrict z,const T *restrict x,const T *restrict y,size_t n,size_t stride); \
void stencil_##S(T *restrict z,const T *restrict x,size_t n,size_t stride,T a,T b,T c); \
T dot_##S(const T *restrict x,const T *restrict y,size_t n,size_t stride);
DECL(float,f32)
DECL(double,f64)
