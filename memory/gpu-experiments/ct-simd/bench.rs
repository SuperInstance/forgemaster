use ct_simd::{BatchSnap, BenchStats};

fn main() {
    for max_c in [1000u64, 10000, 50000] {
        let bs = BatchSnap::new(max_c);
        let stats = BenchStats::run(&bs, 100_000);
        println!("max_c={} triples={} threads={}", max_c, stats.n_triples, stats.n_threads);
        println!("  parallel: {:.0} qps ({:.0} ns/q)", stats.parallel_qps, stats.parallel_ns as f64 / stats.n_queries as f64);
        println!("  sequential: {:.0} qps ({:.0} ns/q)", stats.sequential_qps, stats.sequential_ns as f64 / stats.n_queries as f64);
        println!("  speedup: {:.1}x", stats.speedup);
    }
}
