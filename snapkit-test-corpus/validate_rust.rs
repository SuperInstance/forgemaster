// Validate snapkit Rust implementation against the test corpus.
// Build: rustc --edition 2021 validate_rust.rs -o validate_rust && ./validate_rust
// Uses binary corpus format (run convert_corpus.py first).

use std::fs;
use std::io::Read;

const SQRT3: f64 = 1.7320508075688772;

#[derive(Debug)]
struct TestCase {
    id: u32,
    x: f64,
    y: f64,
    exp_a: i32,
    exp_b: i32,
    snap_error: f64,
    snap_error_max: f64,
}

fn snap_error(x: f64, y: f64, a: i32, b: i32) -> f64 {
    let lx = a as f64 - b as f64 / 2.0;
    let ly = b as f64 * SQRT3 / 2.0;
    ((x - lx).powi(2) + (y - ly).powi(2)).sqrt()
}

fn eisenstein_snap(x: f64, y: f64) -> (i32, i32) {
    let b_float = 2.0 * y / SQRT3;
    let a_float = x + y / SQRT3;

    let a_lo = a_float.floor() as i32;
    let b_lo = b_float.floor() as i32;

    let mut best_a: i32 = 0;
    let mut best_b: i32 = 0;
    let mut best_err: f64 = f64::MAX;

    for da in 0..=1i32 {
        for db in 0..=1i32 {
            let ca = a_lo + da;
            let cb = b_lo + db;
            let err = snap_error(x, y, ca, cb);
            if err < best_err - 1e-15 {
                best_a = ca; best_b = cb; best_err = err;
            } else if (err - best_err).abs() < 1e-15 {
                if ca < best_a || (ca == best_a && cb < best_b) {
                    best_a = ca; best_b = cb;
                }
            }
        }
    }

    for da in -1..=1i32 {
        for db in -1..=1i32 {
            let ca = best_a + da;
            let cb = best_b + db;
            let err = snap_error(x, y, ca, cb);
            if err < best_err - 1e-15 {
                best_a = ca; best_b = cb; best_err = err;
            } else if (err - best_err).abs() < 1e-15 {
                if ca < best_a || (ca == best_a && cb < best_b) {
                    best_a = ca; best_b = cb;
                }
            }
        }
    }

    (best_a, best_b)
}

fn read_u32_le(data: &[u8], offset: &mut usize) -> u32 {
    let bytes: [u8; 4] = data[*offset..*offset+4].try_into().unwrap();
    *offset += 4;
    u32::from_le_bytes(bytes)
}

fn read_i32_le(data: &[u8], offset: &mut usize) -> i32 {
    let bytes: [u8; 4] = data[*offset..*offset+4].try_into().unwrap();
    *offset += 4;
    i32::from_le_bytes(bytes)
}

fn read_f64_le(data: &[u8], offset: &mut usize) -> f64 {
    let bytes: [u8; 8] = data[*offset..*offset+8].try_into().unwrap();
    *offset += 8;
    f64::from_le_bytes(bytes)
}

fn parse_corpus(filename: &str) -> Vec<TestCase> {
    let mut file = fs::File::open(filename).expect("Cannot open corpus file");
    let mut data = Vec::new();
    file.read_to_end(&mut data).expect("Cannot read corpus file");

    let mut cases = Vec::new();
    let mut offset = 0;
    let record_size = 4 + 8 + 8 + 4 + 4 + 8 + 8; // 44 bytes per record

    while offset + record_size <= data.len() {
        let id = read_u32_le(&data, &mut offset);
        let x = read_f64_le(&data, &mut offset);
        let y = read_f64_le(&data, &mut offset);
        let exp_a = read_i32_le(&data, &mut offset);
        let exp_b = read_i32_le(&data, &mut offset);
        let snap_error = read_f64_le(&data, &mut offset);
        let snap_error_max = read_f64_le(&data, &mut offset);

        cases.push(TestCase { id, x, y, exp_a, exp_b, snap_error, snap_error_max });
    }

    cases
}

fn main() {
    let cases = parse_corpus("corpus/snap_corpus.bin");
    if cases.is_empty() {
        eprintln!("ERROR: No cases parsed. Run convert_corpus.py first.");
        std::process::exit(1);
    }

    let mut passed = 0u32;
    let mut failed = 0u32;
    let mut errors: Vec<String> = Vec::new();

    for case in &cases {
        let (a, b) = eisenstein_snap(case.x, case.y);
        let err = snap_error(case.x, case.y, a, b);

        let mut ok = true;
        if a != case.exp_a {
            errors.push(format!("Case {}: a={}, expected={}", case.id, a, case.exp_a));
            ok = false;
        }
        if b != case.exp_b {
            errors.push(format!("Case {}: b={}, expected={}", case.id, b, case.exp_b));
            ok = false;
        }
        if err > case.snap_error_max + 1e-10 {
            errors.push(format!("Case {}: snap_error={} > max={}", case.id, err, case.snap_error_max));
            ok = false;
        }

        if ok { passed += 1; } else { failed += 1; }
    }

    println!("Results: {}/{} passed, {} failed", passed, cases.len(), failed);

    if !errors.is_empty() {
        for e in errors.iter().take(20) {
            println!("  {}", e);
        }
        std::process::exit(1);
    } else {
        println!("All cases passed ✓");
    }
}
