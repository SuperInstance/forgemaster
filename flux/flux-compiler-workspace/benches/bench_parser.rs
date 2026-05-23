use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use std::fs;

// Re-export or use the actual parser module when integrated.
// For now, we benchmark against a stub that exercises the pest parser.

mod parser_support {
    use pest::Parser;

    #[derive(pest_derive::Parser)]
    #[grammar = "guard.pest"]
    pub struct GuardParser;

    pub fn parse_guard(input: &str) -> Result<
        pest::iterators::Pairs<'_, super::guard_support::Rule>,
        pest::error::Error<super::guard_support::Rule>,
    > {
        GuardParser::parse(super::guard_support::Rule::file, input)
    }
}

// Simple range: one field, one range constraint
const SIMPLE_RANGE: &str = r#"temperature IN 0.0..100.0"#;

// Complex nested: multiple fields, AND/OR/NOT, parenthesized groups
const COMPLEX_NESTED: &str = r#"
altitude IN 0..400
airspeed IN 0..60
(sensor_a IN 0.0..100.0) OR (sensor_b IN 0.0..50.0)
NOT status IN ["faulted", "unknown"]
rpm IN 800..6500 AND coolant_temp < 105.0
firmware_version IS "2.4.1-stable"
geo_zone IN ["alpha", "bravo", "charlie"]
"#;

// Full flight envelope: all features including temporal, security, metadata
const FULL_FLIGHT_ENVELOPE: &str = r#"
# Flight Envelope Constraint — v2.1
# Audit: OPS-2024-0315

@version "2.1.0"
@audit_id "OPS-2024-0315"
@authorized_by "chief_pilot:casey.d"

altitude IN 0..400
airspeed IN 0..60

airspeed <= 50
  FOR duration >= 60s
  WITH tolerance < 2000ms

geo_zone IN ["alpha", "bravo", "charlie", "delta"]

NOT flight_mode IN ["faulted", "maintenance"]

SECURITY clearance >= "pilot"
command.signature TRUSTED

@expires "2025-03-15T00:00:00Z"
"#;

fn bench_simple_range(c: &mut Criterion) {
    c.bench_function("parse_simple_range", |b| {
        b.iter(|| {
            let _ = parser_support::parse_guard(black_box(SIMPLE_RANGE));
        })
    });
}

fn bench_complex_nested(c: &mut Criterion) {
    c.bench_function("parse_complex_nested", |b| {
        b.iter(|| {
            let _ = parser_support::parse_guard(black_box(COMPLEX_NESTED));
        })
    });
}

fn bench_full_flight_envelope(c: &mut Criterion) {
    c.bench_function("parse_full_flight_envelope", |b| {
        b.iter(|| {
            let _ = parser_support::parse_guard(black_box(FULL_FLIGHT_ENVELOPE));
        })
    });
}

fn bench_parametrized_line_count(c: &mut Criterion) {
    let mut group = c.benchmark_group("parametrized_lines");

    for &line_count in &[1, 5, 10, 25, 50, 100] {
        let input = generate_input(line_count);
        group.bench_with_input(
            BenchmarkId::new("lines", line_count),
            &input,
            |b, input| {
                b.iter(|| {
                    let _ = parser_support::parse_guard(black_box(input));
                })
            },
        );
    }
    group.finish();
}

/// Generate a GUARD input with the given number of constraint lines.
fn generate_input(lines: usize) -> String {
    let mut out = String::with_capacity(lines * 60);
    for i in 0..lines {
        out.push_str(&format!("field_{} IN 0.0..100.0\n", i));
    }
    out
}

criterion_group!(
    benches,
    bench_simple_range,
    bench_complex_nested,
    bench_full_flight_envelope,
    bench_parametrized_line_count,
);
criterion_main!(benches);
