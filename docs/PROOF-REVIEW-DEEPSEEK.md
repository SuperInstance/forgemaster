### 1. Fleet Rigidity (Laman)  
**CORRECT**. Laman's theorem is a fundamental result: a 2D graph is minimally rigid iff it has exactly \(2N-3\) edges and no subgraph violates the \(2k-3\) edge condition. Verification for \(N=3..100\) is empirical (numerical checks), but the theorem itself is proven for all \(N\).  

### 2. Optimal Coupling \(\alpha^*\)  
**PARTIALLY CORRECT**. The formula \(\alpha^* = 2/(\lambda_2 + \lambda_N)\) is spectrally derived for ideal consensus and correct. However, experimental convergence at \(1.076\times\) the predicted rate indicates a deviation, likely due to unmodeled dynamics (e.g., noise, delays), making the claim incomplete in practice.  

### 3. Mutual Information I(X;Y)=0 Below Deadband  
**INCORRECT** — now **CORRECTED**. The original claim was disproved: I(X;Y)=0 implies statistical independence, which is not guaranteed merely because drift is below a deadband δ. Correlated processes could have low drift but high mutual information (e.g., synchronized oscillators). The claim confused bounded drift with independence.

**Correction applied (2025-05-22):** Theorem 2.1 has been rewritten as **Theorem 2.1 (Deadband Sparsity)** — a weaker but correct theorem about the sparsity of transmitted corrections, not mutual information. The deadband filter is a deterministic threshold: below ε, no useful correction is transmitted. The expected correction rate is P(|X|≥ε)·N, which is exponentially small for σ≪ε. No mutual information claim is made. Appendix C also corrected accordingly.  

### 4. Zero Drift with Exact Arithmetic  
**CORRECT**. Using exact rational arithmetic (e.g., Python `Fraction`) eliminates floating-point rounding errors. For \(K\) operations (e.g., 10K beats), zero drift is expected and obvious—rational arithmetic preserves precision algebraically.  

### 5. Byzantine Fault Tolerance  
**PARTIALLY CORRECT**. The bound \(N \geq 3f+1\) is standard for BFT consensus (e.g., PBFT). Reputation-weighted trimmed mean may enhance robustness but does not alter the fundamental bound. Topology-awareness (e.g., communication graphs) affects efficiency but not the minimum node count for information-theoretic safety.  

### 6. Memoir Compression to \(O(\log T)\) Tiles  
**PARTIALLY CORRECT**. The claim is **proven** only if the paper provides a rigorous information-theoretic argument (e.g., entropy bounds). Otherwise, it is conjectural. \(O(\log T)\) compression is plausible for state machines with bounded incremental state (e.g., counters), but depends on the PLATO tile model’s expressiveness.
