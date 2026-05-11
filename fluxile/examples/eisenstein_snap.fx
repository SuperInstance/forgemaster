// eisenstein_snap.fx — Snap a point to the Eisenstein lattice
fn eisenstein_snap(x: f32, y: f32) -> i32 {
    let a = round(x);
    let b = round(y - a * 0.5);
    // Constraint: norm must be non-negative on the lattice
    constraint a * a + b * b >= 0;
    let result = a as i32 + b as i32;
    return result;
}
