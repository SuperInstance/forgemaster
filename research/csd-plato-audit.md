# PLATO Room CSD Audit (50-room sample)

## Methodology
- Randomly sampled 50 rooms from 1400+ PLATO rooms
- Extracted verifiable claims from tile text
- Checked claim pairs for conflicts
- Computed CSD = 1 - (conflicts / total_pairs)

## Results
- 50/50 rooms: CSD = 1.000 (HIGH COHERENCE)
- 0 conflicts detected in sample
- Most rooms have 3-5 tiles with few claim pairs

## Known Exception
- `deadband_protocol` (694 tiles): CSD = 0.49, 3600/7125 conflicts
  - This room was NOT in the random sample
  - It's an outlier: very large room with many overlapping claims

## Implication
Most PLATO rooms are coherent (small, focused, few conflicts). The CSD metric's value is in detecting fragmentation in large rooms where manual review is impractical.
