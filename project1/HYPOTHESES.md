# Pre-experiment hypotheses

Recorded before the project measurements. Three required kernels: AXPY, elementwise multiply,
and a 1D three-point stencil. A strict floating-point dot product is an additional negative case.

1. NEON should help regular contiguous loops with cache-resident arrays. Its 128-bit width
   gives four float32 or two float64 lanes, but lane count is not a guaranteed speedup.
2. Gains should compress for footprints larger than the observable CPU caches because useful
   data movement becomes dominant. The precise size of Apple system-level cache is not assumed.
3. Misalignment and scalar remainders should matter most for small arrays; call/loop overhead
   will also be visible there. NEON has no AVX-512-style masked tail in this experiment.
4. Strides 2, 4, and 8 should lower useful throughput and may stop auto-vectorization.
5. float64 has fewer lanes and larger traffic, so it should generally achieve fewer elements/s.
6. Strict left-to-right floating-point dot-product summation may resist auto-vectorization;
   compiler reports must verify this, rather than attributing every optimization to SIMD.

All builds use the same floating-point contraction policy and optimization level. No fast-math.
The scalar build additionally disables loop and SLP vectorization. Required experiments are single-threaded.
