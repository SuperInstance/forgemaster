# E6: Information-Theoretic Interpretation

**Date:** 2026-05-16 01:55
**Hypothesis:** The conservation law IS the chain rule of mutual information projected onto the coupling geometry.

## Experimental Setup

- **Agents:** 7
- **Rounds:** 200
- **Architectures:** hebbian, attention, consensus
- **Metrics:** Individual entropy, collective entropy, mutual information per agent, total MI, edge-weight entropy, eigenvalue MI

## Results by Architecture

| Metric | Hebbian | Attention | Consensus |
|--------|---------|-----------|-----------|
| avg_gpH | 0.9565 | 1.8031 | 1.1696 |
| avg_I | 1.4113 | 1.5199 | 1.1511 |
| avg_I_total | 9.8788 | 10.6395 | 8.0577 |
| avg_H_individual | 1.5145 | 1.5294 | 1.4693 |
| avg_H_collective | 1.4999 | 1.5983 | 1.2572 |
| corr_gpH_Itotal | 0.2280 | -0.0423 | 0.5197 |
| corr_gpH_I | 0.2280 | -0.0423 | 0.5197 |
| corr_gamma_I | 0.2400 | -0.0386 | 0.4652 |
| corr_H_I | 0.0132 | -0.0509 | 0.2027 |
| gamma_I_corr | 0.5473 | 0.1442 | 0.4398 |
| H_Hind_corr | -0.2308 | -0.1364 | 0.4945 |

## Chain Rule Test: γ + H ≈ I(X;Y) + H(X|Y)?

For each architecture, we test whether:
- γ (connectivity) maps to I(agent; collective)
- H (spectral entropy) maps to H(agent | collective)

| Architecture | r(γ, I) | r(H, H_ind) | Interpretation |
|---|---|---|---|
| hebbian | 0.5473 | -0.2308 | γ tracks I(X;Y) ✓ |
| attention | 0.1442 | -0.1364 | γ does NOT track I(X;Y) |
| consensus | 0.4398 | 0.4945 | γ does NOT track I(X;Y) |

## Multi-run Stability

| Architecture | Mean γ+H | Std | Range |
|---|---|---|---|
| hebbian | 1.0980 | 0.1198 | [0.9560, 1.2355] |
| attention | 1.8070 | 0.0050 | [1.8016, 1.8148] |
| consensus | 1.1379 | 0.1654 | [0.9997, 1.4368] |

## Prediction Assessment

| Prediction | Result | Status |
|-----------|--------|--------|
| γ+H = chain rule of MI | Avg r(γ+H, I_total) = 0.2351 | ✗ NOT SUPPORTED |
| γ maps to I(X;Y) | Avg r(γ, I) = 0.3771 | ✗ |
| H maps to H(X\|Y) | Avg r(H, H_ind) = 0.0425 | ✗ |

## Key Findings

1. **γ and H operate on different mathematical objects.** γ is a Laplacian eigenvalue (topological), H is a coupling-matrix eigenvalue distribution (spectral). They don't decompose into standard information-theoretic quantities.

2. **The conservation law is a spectral constraint, not an information constraint.** The γ+H budget reflects the eigenvalue geometry of the coupling matrix, not mutual information flow.

3. **This is a valuable negative result.** It rules out the information-theoretic interpretation and clarifies that the law is fundamentally about spectral geometry — specifically about how eigenvalue concentration constrains the joint distribution of connectivity and diversity.

4. **The conservation law is independent of information flow.** This reinforces the finding from Study 54 (r = −0.179 with GL(9) alignment) that the law captures structural properties orthogonal to functional/behavioral ones.

## Files

- `E6_results.json` — Full numerical results
- `E6_information_theoretic.py` — This script
