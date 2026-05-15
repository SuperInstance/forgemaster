use std::time::Instant;

fn eisenstein_norm(a: i64, b: i64) -> i64 {
    a * a - a * b + b * b
}

#[derive(Clone, Copy)]
struct IntPair { a: i64, b: i64 }

fn eisenstein_snap(x: f64, y: f64) -> IntPair {
    let q = (2.0 / 3.0 * x - 1.0 / 3.0 * y);
    let r = (2.0 / 3.0 * y);
    let mut rq = q.round();
    let mut rr = r.round();
    let rs = (-q - r).round();
    let diff = (rq + rr + rs).abs();
    if diff == 2.0 {
        if (rq - q).abs() > (rr - r).abs() {
            rq = -rr - rs;
        } else {
            rr = -rq - rs;
        }
    }
    IntPair { a: rq as i64, b: rr as i64 }
}

fn constraint_check(a: i64, b: i64, radius: f64) -> bool {
    eisenstein_norm(a, b) as f64 <= radius * radius
}

struct Lcg { state: u64 }
impl Lcg {
    fn new(seed: u64) -> Self { Lcg { state: seed } }
    fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        self.state
    }
    fn rand_int(&mut self, min: i64, max: i64) -> i64 {
        (self.next_u64() as i64).rem_euclid(max - min + 1) + min
    }
    fn rand_f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }
}

fn main() {
    const N: usize = 10_000_000;
    let mut rng = Lcg::new(42);

    let norm_a: Vec<i64> = (0..N).map(|_| rng.rand_int(-1000, 1000)).collect();
    let norm_b: Vec<i64> = (0..N).map(|_| rng.rand_int(-1000, 1000)).collect();
    // Reset rng state for consistency
    let mut rng2 = Lcg::new(42);
    let snap_x: Vec<f64> = (0..N).map(|_| rng2.rand_f64() * 200.0 - 100.0).collect();
    let snap_y: Vec<f64> = (0..N).map(|_| rng2.rand_f64() * 200.0 - 100.0).collect();
    let con_a: Vec<i64> = (0..N).map(|_| rng2.rand_int(-100, 100)).collect();
    let con_b: Vec<i64> = (0..N).map(|_| rng2.rand_int(-100, 100)).collect();
    let con_r: Vec<f64> = (0..N).map(|_| rng2.rand_f64() * 49.0 + 1.0).collect();

    // Benchmark norm
    let mut norm_sum: i64 = 0;
    let start = Instant::now();
    for i in 0..N {
        norm_sum += eisenstein_norm(norm_a[i], norm_b[i]);
    }
    let norm_time = start.elapsed().as_secs_f64();

    // Benchmark snap
    let mut snap_sum: i64 = 0;
    let start = Instant::now();
    for i in 0..N {
        let s = eisenstein_snap(snap_x[i], snap_y[i]);
        
    }
    let snap_time = start.elapsed().as_secs_f64();

    // Benchmark constraint
    let mut con_pass: i64 = 0;
    let start = Instant::now();
    for i in 0..N {
        if constraint_check(con_a[i], con_b[i], con_r[i]) { con_pass += 1; }
    }
    let con_time = start.elapsed().as_secs_f64();

    println!("Rust Results (N={}):", N);
    println!("  eisenstein_norm:  {:.3}s  (sum={})", norm_time, norm_sum);
    println!("  eisenstein_snap:  {:.3}s  (first=({},{})", snap_time, snap_sum);
    println!("  constraint_check: {:.3}s  (pass={})", con_time, con_pass);
    println!("  TOTAL: {:.3}s", norm_time + snap_time + con_time);
}
