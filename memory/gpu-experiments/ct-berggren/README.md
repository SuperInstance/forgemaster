# ct-berggren

Berggren ternary tree — algebraic generation of ALL primitive Pythagorean triples from (3,4,5).

## What It Does

- `BerggrenTree::new(max_c)` — builds the full ternary tree
- `MAT_A`, `MAT_B`, `MAT_C` — the three 3×3 Berggren matrices
- `triple_by_path(&[0,1,2])` — generate triple by matrix path
- `at_level(n)` — enumerate all triples at depth n
- `max_depth()` — tree depth

## The Math

All primitive Pythagorean triples form a ternary tree rooted at (3,4,5). Three matrices generate every child:

```
A = [ 1 -2  2]   B = [1 2 2]   C = [-1 2 2]
    [ 2 -1  2]       [2 1 2]       [-2 1 2]
    [ 2 -2  3]       [2 2 3]       [-2 2 3]
```

## Install

```toml
[dependencies]
ct-berggren = "0.1"
```

## License

MIT
