# cocapn-cli

**Fleet CLI theme — The Abyssal Terminal aesthetic.**

Consistent output formatting for Cocapn fleet tools. Dark background, cyan/magenta accents, amber warnings. Standardized `[TAG  ]` prefix format for agent-parseable output.

## Output Format

```
[PLATO] ████████████████████ 100% | 12.4s
[VALID] 0 hallucination markers | 5,447 tiles checked
[ASK  ] 3 matches for "grammar engine" in 464 domains
[RANK ] compressed_sensing: 0.937 🏆
```

## Fleet Tags

```rust
use cocapn_cli::tags;

println!("{} 5,447 tiles imported", tags::plato());
println!("{} 0 hallucination markers", tags::valid());
```

## Safe-TOPS/W Table

```rust
use cocapn_cli::safe_tops_w_table;

println!("{}", safe_tops_w_table());
```

Output:

| Chip | Raw TOPS/W | Safe-TOPS/W |
|------|-----------|-------------|
| FLUX-LUCID | 24.0 | **20.17** |
| Jetson Orin AGX | 5.7 | **0.00** |
| Groq LPU | 21.4 | **0.00** |

## License

MIT OR Apache-2.0
