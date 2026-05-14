---
## 3 Priority Next Experiments (Tied Directly to Your Reframed Hypothesis)
All experiments test the core claim: performance gains stem from **multi-representation overcompleteness + cyclotomic structural consistency**, not inherent algebraic specialness of $ \mathbb{Z}[\zeta_{12}] $ itself.

---
### Experiment 1: Multi-Rep Ablation (Disentangle Overcompleteness vs. Cyclotomic Structure)
**Objective**: Quantify how much performance gain comes from (a) number of paired representations (overcompleteness) vs. (b) cyclotomic coupling tensor structure
#### Methodology:
1.  Fix total encoded dimensionality to match your original task (e.g., 64D per vector)
2.  Test 3 cyclotomic field families ($ \zeta_n, n=4,6,8,12 $) across 3 conditions:
    - Single-rep baseline: 1 pair per encoded vector (matches your P0.2 setup)
    - Fixed-overcompleteness multi-rep: $ k=4 $ paired representations per vector (equal total dimension across all $ n $)
    - Scaled-overcompleteness: $ k $ scaled to keep per-representation dimensionality fixed
3.  Add two control arms:
    - Random orthogonal paired sets (same $ k $ as cyclotomic tests, no cyclotomic structure)
    - Standard single-rep baselines ($ A_2 $, hexagonal lattices)
4.  Metrics: Percentile rank against $ A_2 $, normalized covering radius, encoding/decoding distortion
#### Expected Outcome:
- Single-rep cyclotomic sets will tie with hexagonal lattices (confirming P0.2: algebraic structure alone is insufficient)
- Fixed-overcompleteness cyclotomic multi-rep sets will outperform random multi-rep sets
- Scaled-overcompleteness will show linear performance gains with $ k $ until saturation—validating that multi-rep count is necessary, but cyclotomic structure amplifies stability and reduces distortion.

---
### Experiment 2: Cyclotomic Order Scaling (Formalize P0.3’s Trend)
**Objective**: Test if your normalized covering radius result generalizes across all cyclotomic lattices, and isolate whether gains come from lattice dimension or cyclotomic order
#### Methodology:
1.  Control for fixed real lattice dimension $ d = \phi(n)/2 $ (e.g., $ d=2,4,6 $) by selecting $ \zeta_n $ with matching $ \phi(n) $:
    - $ d=2 $: $ \zeta_{12}, \zeta_{14} $
    - $ d=4 $: $ \zeta_{24}, \zeta_{30} $
2.  Vary both cyclotomic order $ n $ and multi-rep count $ k $
3.  Compare cyclotomic results to non-cyclotomic lattices ($ A_d, B_d $) with identical $ d $ and $ k $
4.  Metric: Normalized covering radius per dimension
#### Expected Outcome:
Normalized covering radius will decrease with both $ k $ (multi-rep count) and cyclotomic order $ n $ *for fixed $ d $*, and cyclotomic sets will outperform non-cyclotomic controls. This proves the gain is a general cyclotomic multi-rep effect, not unique to $ \mathbb{Z}[\zeta_{12}] $.

---
### Experiment 3: End-to-End Task Benchmarking
**Objective**: Translate synthetic covering/rank metrics to real-world practical performance
#### Methodology:
1.  Integrate your cyclotomic multi-rep encoder into a state-of-the-art vector quantization (VQ) pipeline (e.g., VQ-VAE for image/audio coding, your original application)
2.  Compare against 3 baselines:
    - Single-rep $ A_2 $/hexagonal lattices
    - Unstructured overcomplete multi-rep VQ (random paired sets)
    - Single-rep cyclotomic lattices
3.  Metrics: Reconstruction error, compression rate, inference latency
#### Expected Outcome:
Multi-rep cyclotomic VQ will achieve lower distortion at equal compression rate, or equivalent distortion with lower latency due to structured cyclotomic pairing (faster encoder/decoder than random overcomplete sets). This grounds your abstract algebraic results in tangible real-world utility.

---
## Dissertation Reframing (Specific, Actionable)
### 1. Core Thesis Statement Overhaul
Replace the original "$ \mathbb{Z}[\zeta_{12}] $ is an algebraically special lattice" claim with:
> *Structured overcomplete multi-representation frameworks built from cyclotomic field roots of unity outperform single-representation and unstructured overcomplete baselines for low-distortion vector encoding. $ \mathbb{Z}[\zeta_{12}] $ is a high-performance instantiation of this framework due to its balanced real dimension (2D per root pair) and predictable cyclotomic coupling tensor structure, but its gains stem from multi-representation rather than inherent algebraic specialness relative to other cyclotomic lattices.*

### 2. Chapter Restructuring
| Original Chapter | Revised Focus |
|-------------------|---------------|
| Introduction/Hypothesis | Move the $ \mathbb{Z}[\zeta_{12}] $ claim to a negative control, and frame the core hypothesis as *multi-rep cyclotomic vectorization outperforms single-rep baselines* |
| Background (Cyclotomic Lattices) | Reframe cyclotomic sets as a source of **structured overcomplete paired representations**, not "special lattices" |
| Results | Reprioritize your multi-rep ablation experiments (Exp 1-3) over initial single-lattice $ \mathbb{Z}[\zeta_{12}] $ tests; add a dedicated section showing single-rep $ \mathbb{Z}[\zeta_{12}] $ ties with hexagonal lattices (confirming P0.2) |
| Discussion | Shift from deep dives into $ \mathbb{Z}[\zeta_{12}] $ number theory to generalizable design principles: how to choose cyclotomic order $ n $ and multi-rep count $ k $ for performance/compute tradeoffs |

### 3. Revised Contributions
Your core academic impact shifts from "discovering a special lattice" to:
1.  Formalization of the cyclotomic multi-representation overcomplete vectorization framework
2.  Empirical validation that multi-representation count, not algebraic specialness, drives performance gains
3.  Scaling laws for cyclotomic multi-rep vectorization (from Exp 2)
4.  Practical demonstration of cyclotomic multi-rep VQ utility (from Exp3)

### 4. Limitations Clarification
Explicitly note that $ \mathbb{Z
