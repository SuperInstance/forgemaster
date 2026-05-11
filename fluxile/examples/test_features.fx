// test_features.fx — Test all new language features

// Test 1: for..in range
fn sum_to(n: i32) -> i32 {
    let mut total = 0;
    for i in range(n) {
        total = total + i;
    }
    return total;
}

// Test 2: match expression
fn classify(x: i32) -> i32 {
    match x {
        0 => {
            return 1;
        }
        1 => {
            return 2;
        }
        _ => {
            return 3;
        }
    }
}

// Test 3: let mut (mutable bindings)
fn counter() -> i32 {
    let mut x = 0;
    x = x + 1;
    x = x + 2;
    return x;
}

// Test 4: builtins without type context (round, sqrt)
fn builtin_test(x: f32) -> f32 {
    let a = round(x);
    let b = sqrt(x);
    return a + b;
}

// Test 5: constraint fn (FLUX-C layer)
constraint fn positive(val: i32) {
    require val > 0;
}

// Test 6: strength reduction opportunity (x * 2 → x << 1)
fn shift_test(x: i32) -> i32 {
    return x * 2 + x * 4;
}

// Test 7: constant folding (2 + 3 = 5 at compile time)
fn fold_test() -> i32 {
    let a = 2 + 3;
    let b = 10 * 5;
    return a + b;
}

// Test 8: vec9 / vdot
fn vec_test(a: vec9, b: vec9) -> f32 {
    return vdot(a, b);
}

// Test 9: agent block
agent Coordinator {
    fn handle() {
        tell(0, 1);
    }
}

// Test 10: while loop
fn countdown(n: i32) -> i32 {
    let mut i = n;
    while i > 0 {
        i = i - 1;
    }
    return i;
}
