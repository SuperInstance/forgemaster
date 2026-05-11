// constraint_check.fx — Constraint function with bounds checking
constraint fn check_bounds(val: i32, min: i32, max: i32) {
    require min <= val;
    require val <= max;
}

fn safe_divide(a: i32, b: i32) -> i32 {
    constraint b != 0;
    return a / b;
}

fn test() -> i32 {
    let x = 42;
    check_bounds(x, 0, 100);
    let result = safe_divide(x, 6);
    return result;
}
