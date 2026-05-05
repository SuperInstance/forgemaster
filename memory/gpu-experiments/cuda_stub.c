/* cuda_stub.c — CPU-only fallback when nvcc is unavailable at build time.
   Provides the same symbol names as cuda_kernel.cu so the rest of the code
   compiles and links without modification.  Both functions advertise "no GPU". */

int cuda_device_count(void) {
    return 0;
}

int cuda_snap_batch(
    const float *query_xs,    const float *query_ys,    int n_queries,
    const float *manifold_xs, const float *manifold_ys, int n_manifold,
    float *out_distances,     int *out_indices
) {
    /* Unused parameters — silence warnings */
    (void)query_xs; (void)query_ys; (void)n_queries;
    (void)manifold_xs; (void)manifold_ys; (void)n_manifold;
    (void)out_distances; (void)out_indices;
    return -1;  /* signals: not implemented */
}
