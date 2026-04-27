# ct-learned

Learned index structures for O(1) Pythagorean snap — CDF prediction with linear correction.

## What It Does

- `LearnedIndex::train(data, segments)` — piecewise linear CDF model
- `index.predict(angle)` — O(1) index prediction
- `index.search(angle, angles, epsilon)` — prediction + linear scan correction
- `verify(index, angles, tests, epsilon)` — accuracy verification

## Install

```toml
[dependencies]
ct-learned = "0.1"
```

## License

MIT
