# Pre-experiment hypotheses

Recorded before the project measurements.

1. A randomized dependent pointer chain should reveal rising latency as its working set exceeds
   local caches. Sequential chains can benefit from prefetching and are not interchangeable with random latency.
2. Non-unit memory access granularity should lower useful byte throughput; source-level bytes
   must not be presented as measured DRAM bus traffic.
3. Additional traffic threads should initially increase bandwidth; eventually gains should
   diminish while an independent dependent-load probe becomes slower.
4. Read/write mixes should differ because stores may require ownership and writeback. Loaded
   probe latency measures read latency under each load, not persistence latency of stores.
5. At equal touched-line count, spreading one node per native 16KiB page should increase
   translation pressure relative to 128-byte-spaced nodes. Cache conflicts remain a confounder;
   elapsed time or VM page faults alone cannot establish hardware TLB-miss counts.
6. Reusing a small cache-resident buffer can give a misleadingly high apparent DRAM bandwidth.

The Mac has heterogeneous cores and dynamic frequency. QoS is not strict pinning. A separate
L3 cannot be assumed from an x86 diagram. A prior 2MiB explicit superpage allocation failed;
that condition will be rechecked and reported rather than replaced with simulated huge-page data.
