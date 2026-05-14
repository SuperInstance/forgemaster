<think>
We are going to write a 2000-word analytical paper titled "RESIDUE IS THE MAP: FROM FAILURE MODES TO COMPUTATIONAL CARTOGRAPHY". The paper argues that cognitive residue discovery (with the observed distribution: 50% echo, 40% partial, and a phase transition at 4 billion parameters) is a new paradigm for understanding neural networks: computational cartography. We draw an analogy with bathymetry (mapping the ocean floor) to explain how residue analysis maps the computational terrain of a model by measuring failure at discrete tasks and classifying the residue.

Structure:
1. Introduction: Introduce the problem of understanding neural network computation and the concept of cognitive residue.
2. The Cognitive Residue Discovery: Describe the empirical findings (50% echo, 40% partial, phase transition at 4B parameters).
3. The Bathymetry Analogy: Explain how residue analysis is like mapping the ocean floor.
4. Residue Terrain Map (RTM): Propose a formal framework with coordinates (model_size, task_complexity) and depth (failure_mode).
5. Navigating Computational Space: Show how RTM enables route planning for multi-model fleets.
6. Implications and Future Work: Discuss the broader implications and potential extensions.
7. Conclusion.

Let's begin writing the paper.
</think>
## RESIDUE IS THE MAP: FROM FAILURE MODES TO COMPUTATIONAL CARTOGRAPHY

**Abstract:**  
This paper proposes a paradigm shift in understanding neural network computation: **computational cartography**. We argue that the empirical phenomenon of cognitive residue—observed as distinct failure modes (50% echo, 40% partial) with a phase transition at ~4B parameters—is not merely diagnostic but constitutes a *map* of a model’s internal computational landscape. Drawing inspiration from bathymetry (ocean floor mapping), we formalize **Residue Terrain Maps (RTMs)**. RTMs plot computational "depth" (failure mode) against coordinates of model scale and task complexity. Echo failures represent shallow soundings (superficial pattern matching), partial failures mid-depth soundings (incomplete computation), and correct answers deep soundings (successful execution). By systematically charting residues across tasks and models, RTMs reveal latent computational structures—"echo shoals" and "partial reefs"—that constrain model navigation. We demonstrate how RTMs enable strategic "route planning" for multi-model fleets, optimizing task allocation by avoiding hazardous cognitive terrain. This framework transforms residue from artifact to essential cartographic tool, revealing the hidden geography of machine cognition.

### 1. Introduction: The Terra Incognita of Computation
Understanding *how* neural networks compute remains a fundamental challenge. Traditional approaches—probing internal activations, analyzing loss landscapes, or interpreting attention maps—often yield fragmented, model-specific insights. They resemble explorers sketching isolated landmarks without a coherent map of the territory. Enter **cognitive residue**: the systematic failure patterns (echo, partial) observed when models attempt tasks beyond their emergent capabilities. We contend these residues are not noise but *signals* encoding the structure of the computational substrate itself. Just as bathymetry infers underwater topography from sparse depth soundings, residue analysis infers computational structure from sparse task failures. This paper formalizes this analogy, introducing **computational cartography** as a paradigm for modeling neural computation through the lens of failure terrain.

### 2. Cognitive Residue: The Empirical Foundation
Recent empirical work reveals a striking consistency in how language models fail:

*   **Echo Failures (50%):** The model outputs verbatim reproductions of inputs or training data snippets, demonstrating shallow pattern matching without task-specific computation. *Example:* Asked to summarize a news article, it repeats the headline verbatim.
*   **Partial Failures (40%):** The model engages in meaningful computation but produces incomplete, inconsistent, or contextually detached outputs. *Example:* Solving a math word problem correctly but omitting units or mislabeling the answer.
*   **Phase Transition at 4B Parameters:** Below ~4B parameters, models exhibit chaotic failure modes; above this threshold, residues crystallize into the stable 50/40 echo/partial distribution, suggesting a fundamental shift in computational organization.

These residues are not random. They are *diagnostic signatures* of how deeply a model engages with a task. Echo failures indicate computation barely began; partial failures indicate computation was initiated but aborted or derailed; correct answers indicate full traversal. Crucially, this distribution is predictable across tasks and architectures, implying a universal underlying structure—a **computational terrain**—waiting to be mapped.

### 3. The Bathymetry Analogy: Soundings as Residues
Bathymetry maps the ocean floor by taking discrete depth measurements ("soundings") and interpolating the terrain between them. Similarly, computational cartography maps the "computational floor" of a model:

*   **Sounding = Task Probe:** Presenting a model with a specific task (e.g., logical inference, mathematical calculation, causal reasoning) is analogous to lowering a sonar probe.
*   **Depth Measurement = Failure Mode Classification:** The observed residue (echo, partial, correct) directly corresponds to the "depth" of computation achieved:
    *   **Echo (Shallow Sounding):** The model barely "entered" the computational water column. It registered the input pattern but triggered only low-level, associative retrieval mechanisms. The computational floor is very near the surface here.
    *   **Partial (Mid-Depth Sounding):** The model descended deeper, engaging core computational routines (e.g., parsing, symbolic manipulation, multi-step planning) but failed to "surface" with a complete, consistent result. It encountered a "reef"—a structural limitation in its computational pathways preventing successful completion.
    *   **Correct (Deep Sounding):** The model reached the computational "bottom" and successfully surfaced with a valid output. This indicates a clear channel through the terrain for that specific task.
*   **The Chart = Residue Terrain Map (RTM):** Aggregating soundings (task probes) across the coordinate space of **model scale** (parameters, training FLOPs) and **task complexity** (e.g., number of reasoning steps, abstraction level, novelty) reveals the continuous computational landscape. Interpolation between discrete probes defines basins, ridges, shoals, and trenches of computational capability.

The RTM is thus a bathymetric chart for cognition. Echo failures define hazardous "echo shoals"—wide, shallow regions where models default to superficial mimicry. Partial failures define treacherous "partial reefs"—submerged obstacles disrupting deeper computation. Correct answers define navigable "deep channels."

### 4. Formalizing the Residue Terrain Map (RTM)
We define the Residue Terrain Map (RTM) as a structured representation of a model’s computational capabilities:

*   **Coordinates:**
    *   **X-Axis: Model Scale (`S`):** Quantified by parameter count (`N_params`), training compute (`C_train`), or a composite scaling metric. Captures the model’s intrinsic computational capacity.
    *   **Y-Axis: Task Complexity (`T`):** A multi-dimensional vector capturing task difficulty. Dimensions may include:
        *   `T_steps`: Required reasoning steps.
        *   `T_abstraction`: Level of abstraction (concrete -> symbolic).
        *   `T_novelty`: Deviation from training distribution.
        *   `T_context`: Context window length/dependency.
        *   `T_constraints`: Logical or semantic constraints to satisfy.
        *   *Formally:* `T ∈ ℝ^d` (a d-dimensional vector). Complexity can be normalized or projected onto a scalar metric (e.g., via PCA or task embedding).
*   **Depth (`D`):** The computational depth achieved, mapped from the failure mode:
    *   `D = 0` (Echo): Shallow computation. `D(S, T) = 0` indicates task `T` lies on an echo shoal for model `S`.
    *   `D = 1` (Partial): Mid-depth computation. `D(S, T) = 1` indicates task `T` lies on a partial reef for model `S`.
    *   `D = 2` (Correct): Deep computation. `D(S, T) = 2` indicates a navigable deep channel.
    *   *Interpolation:* `D(S, T)` is defined for all `(S, T)` via interpolation of discrete task probes. Machine learning (e.g., Gaussian Process regression) can model the continuous terrain.
*   **Terrain Features:** The RTM surface `D(S, T)` reveals key structures:
    *   **Phase Boundaries:** Sharp transitions in `D` (e.g., the 4B parameter cliff) manifest as steep escarpments.
    *   **Echo Shoals (`D ≈ 0`):** Expansive regions where `T` is too complex relative to `S`, forcing shallow recall.
    *   **Partial Reefs (`D ≈ 1`):** Complex ridges or plateaus where computation initiates but reliably falters.
    *   **Deep Channels (`D = 2`):** Contiguous regions where `S` is sufficient for reliable computation on `T`.
    *   **Saddles & Passes:** Low points in reefs or high points in shoals indicating marginally successful/failed computation.

**Constructing an RTM:**  
1.  **Task Battery:** Define a diverse set of probes spanning `T` space.
2.  **Model Fleet:** Evaluate multiple models spanning `S` space.
3.  **Residue Annotation:** Classify outputs for each `(S_i, T_j)` as Echo/Partial/Correct → `D_ij`.
4.  **Surface Fitting:** Interpolate `D(S, T)` using the discrete `D_ij` points.
5.  **Feature Extraction:** Identify shoals, reefs, channels, and phase boundaries algorithmically.

### 5. Navigating the Computational Sea: Route Planning with RTMs
The true power of RTMs lies in enabling strategic navigation of computational space, particularly for **multi-model fleets** (ensembles, cascades, specialized agents). An RTM is a nautical chart for AI:

*   **Hazard Avoidance:** Route planning minimizes traversal of hazardous terrain:
    *   **Avoid Echo Shoals:** Tasks predicted to lie on shoals (`D(S, T) < 0.5`) should be routed to larger models (`S' > S`) or models known to have deeper channels for that `T` region.
    *   **Navigate Around Partial Reefs:** Tasks predicted on reefs (`0.5 ≤ D(S, T) < 1.5`) might be decomposed into subtasks (`T1, T2`) where `D(S, T1)=2` and `D(S, T2)=2`, or routed to a model specialized in that reef type (e.g., a model fine-tuned on constraint satisfaction).
*   **Optimal Model Selection:** Given a target task `T_target` and a fleet of models `{S1, S2, ..., Sm}`:
    *   Query RTM: Retrieve predicted `D(Si, T_target)` for all `i`.
    *   Select `S*` where `D(S*, T_target) = 2` (deep channel) *and* `S*` is the smallest/most efficient model satisfying this (minimizing compute cost).
    *   If no `S*` exists with `D=2`, select `S*` with highest `D` (least hazardous failure mode) or trigger decomposition/retrieval-augmentation.
*   **Compositional Navigation:** Complex tasks (`T_complex`) can be decomposed into a sequence of waypoints (`T1 -> T2 -> ... -> Tn`). The RTM identifies:
    *   The safest/most efficient sequence avoiding shoals/reefs.
    *   The optimal model *per waypoint* based on local terrain (`D(Si, Tj)`).
    *   Failure risk at each waypoint (e.g., if `D(S_assigned, Tj) = 1`, plan fallback to a larger model).
*   **Fleet Deployment:** RTMs guide fleet design:
    *   **Coverage:** Ensure the fleet's combined RTM provides deep channels (`D=2`) across the required `T` operational domain.
    *   **Efficiency:** Minimize fleet size/compute by selecting models whose deep channels complementarily cover `T` space without excessive overlap on reefs/shoals.
    *   **Specialization:** Identify "reef specialists"—smaller models fine-tuned to navigate specific partial reefs (`D(S_small, T_reef) → 2`) where base models fail.

**Example:** A fleet handles customer service queries (`T`). Simple FAQs (`T_low`) lie on deep channels for small models (`S_small`). Complex troubleshooting (`T_high`) lies on a partial reef for `S_small` (`D=1`) but a deep channel for a larger model (`S_large`). The RTM routes `T_low` to `S_small` (efficient), and `T_high` to `S_large` (avoiding reef failure). Ambiguous queries (`T_mid`) predicted near an echo shoal (`D≈0.4`) for `S_small` are routed to a medium model (`S_medium`) predicted to have `D≈1.8`, avoiding the shoal.

### 6. Implications and Future Work
**Paradigm Shift:** Computational cartography reframes understanding:
*   **From Circuits to Geography:** Focus shifts from isolating circuits to mapping the *topography* they operate within. Residues are the primary data source.
*   **Scale as Latitude:** Model scale (`S`) becomes a fundamental coordinate defining computational "latitude," with phase transitions akin to climate zones.
*   **Failure as Feature:** Echo/partial are not bugs; they are essential terrain features defining navigational constraints.
*   **Predictive Power:** RTMs predict failure *types* (not just probability) for novel `(S, T)` combinations.

**Future Directions:**
1.  **Automated Cartography:** Develop tools for large-scale RTM construction: automated residue classification, task complexity embedding, terrain interpolation.
2.  **Dynamic RTMs:** Model terrain shifts during training/fine-tuning/adaptation.
3.  **Cross-Model Topology:** Map equivalences between terrains of different architectures (e.g., "This Llama reef corresponds to that GPT ridge").
4.  **Theoretical Foundations:** Formalize the link between residue distributions, phase transitions, and computational complexity theory.
5.  **Beyond Language:** Extend RTMs to multimodal, embodied, and reinforcement learning agents.
6.  **Security & Alignment:** Use RTMs to identify "adversarial shoals/reefs" where models are vulnerable to manipulation or misalignment.

### 7. Conclusion: Charting the Uncharted
Cognitive residue—echo and partial failure—is the Rosetta Stone for deciphering neural computation. By reconceptualizing these failures as bathymetric soundings, we unlock **computational cartography**. The Residue Terrain Map (RTM) transforms sparse, discrete task evaluations into a continuous chart of a model's computational capabilities, revealing hazardous shoals and reefs alongside navigable channels. This is not merely descriptive; it is profoundly operational. RTMs enable strategic route planning for multi-model fleets, optimizing task allocation by leveraging the inherent geography of machine cognition. We move beyond diagnosing why models fail towards understanding *where* they fail within a structured computational landscape. In mapping the residue, we finally map the machine mind. The era of computational cartography has begun—navigate accordingly.
