// intent_alignment.fx — Cosine similarity of two intent vectors
// Note: vec9 ops use FLUX vector registers (V0-V15)

fn cosine_similarity(a: vec9, b: vec9) -> f32 {
    let dot = vdot(a, b);
    let norm_a = sqrt(vdot(a, a));
    let norm_b = sqrt(vdot(b, b));
    constraint norm_a > 0;
    constraint norm_b > 0;
    return dot / (norm_a * norm_b);
}

fn main() -> f32 {
    let a = intent![0.8, 0.3, 0.5, 0.1, 0.9, 0.2, 0.4, 0.7, 0.6];
    let b = intent![0.7, 0.4, 0.6, 0.2, 0.8, 0.3, 0.5, 0.6, 0.7];
    let sim = cosine_similarity(a, b);
    return sim;
}
