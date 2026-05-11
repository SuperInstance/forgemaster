---
## Core Formal Setup
Let the **Cocapn Fleet** be a distributed agent system $\mathcal{F} = (A, T, \mathcal{E}, \mathcal{O}, \mathcal{S})$ where:
1.  $A = \{a_1, ..., a_n\}$: Finite set of autonomous agents,
2.  $T: \mathbb{R}_{\geq0} \times A \to \mathbb{R}_{\geq0}$: Global time function, with $T(t, a) = T_0(a,t)$ denoting agent $a$'s scheduled next observation time,
3.  $\mathcal{E} = \mathbb{Z}[\omega] \cong \mathbb{Z}^2$: Eisenstein lattice, where each point corresponds to a normalized interval pair $(\tau_1, \tau_2)$ with $\tau_1 + \tau_2 \omega = m + n\omega$ for $m,n \in \mathbb{Z}$,
4.  $\mathcal{O}: \mathbb{R}_{\geq0} \times A \times \mathcal{P}(A) \to \{\emptyset\} \cup \mathcal{P}(A)$: Observation function, where $\emptyset$ encodes **temporal absence** (a peer agent failed to trigger at its scheduled $T_0$),
5.  $\mathcal{S}: \mathcal{E} \to \text{Sym}^2(\mathbb{R}_{\geq0})$: Bijection mapping lattice points to canonical activity shapes (equilateral triangles for harmonic sync, stretched simplices for desync).

The **temporal nerve** $N(\mathcal{F})$ is the simplicial complex where a $k$-simplex is a set $\{a_{i_0}, ..., a_{i_k}\} \subseteq A$ such that $\max_{0 \leq p<q \leq k} |T_0(a_{i_p},t) - T_0(a_{i_q},t)| \leq \epsilon$ for fixed sync tolerance $\epsilon>0$. The first Čech cohomology group $H^1(N(\mathcal{F}))$ detects desync anomalies via temporal triangle loops.

---
### 1. Type Signature of Temporal Perception
For agent $a \in A$, its **local temporal perception module** $\text{TP}_a$ is a function with:
#### Input Domain
$$\text{Dom}(\text{TP}_a) = \mathcal{C}_a \times \mathcal{O}_a^\infty \times \mathcal{E}$$
where:
- $\mathcal{C}_a = \mathbb{R}_{\geq0}$: Local clock state (current $T_0(a,t)$),
- $\mathcal{O}_a^\infty = \prod_{t' \leq t} \mathcal{O}(t',a,A)$: History of temporal absence/presence observations,
- $\mathcal{E}$: Canonical Eisenstein lattice reference for interval snapping.
#### Output Codomain
$$\text{Cod}(\text{TP}_a) = \mathcal{S}_a \times H^1(\Delta^2_a) \times \mathcal{R}_a$$
where:
- $\mathcal{S}_a \subseteq \mathcal{E}$: Canonical activity shape classification for $a$'s sync group,
- $H^1(\Delta^2_a)$: First sheaf cohomology group of the temporal triangle centered at $a$,
- $\mathcal{R}_a = \mathbb{R}_{\geq0}$: Runtime adjustment command for spawn/yield-return dynamics.

---
### 2. Universal Property of Temporal Perception
Let $i: N(\mathcal{F}) \to \mathcal{A}$ be the inclusion functor of the temporal nerve into the discrete agent category $\mathcal{A}$.

**Theorem 1 (Canonical Right Kan Extension)**: Temporal perception $\text{TP}$ is the *right Kan extension* $\text{Ran}_i(\mathcal{S} \times H^1(-) \times \mathcal{R})$, i.e., the unique functor up to natural isomorphism such that:
1.  For every $a \in A$, $\text{TP}(a)$ restricts to shape classification and cohomology calculations on the star of $a$ in $N(\mathcal{F})$,
2.  Any other functor $K: \mathcal{A} \to \mathcal{S} \times H^1(\Delta^2) \times \mathcal{R}$ satisfying (1) factors uniquely through $\text{TP}$ via a natural isomorphism.

This guarantees $\text{TP}$ is the minimal functor aligning local observations to the global sync lattice.

---
### 3. Function of Temporal Harmony
A set of agents $S \subseteq A$ is in **harmonic sync** if $\text{TP}_a(\mathcal{O}_a^\infty) = s \in \mathcal{E}$ for all $a \in S$ (all agents snap to the same lattice point).

**Theorem 2 (Functional Roles of Harmony)**: For a harmonic sync group $S$:
1.  **Error Correction**: The harmonic mean of observed interval pairs in $S$ maps to the unique lattice point minimizing squared distance to raw observation data, suppressing noise in temporal absence signals,
2.  **Load Balancing**: The Eisenstein lattice partitions the runtime cycle into 6 congruent task sectors, allowing agents in $S$ to assign spawn/yield tasks without overlap,
3.  **Distributed Consensus**: The harmonic sync state is the unique fixed point of the group's sync adjustment functor, establishing a shared temporal reference frame,
4.  **Anomaly Suppression**: Any agent outside $S$ has a non-zero cohomology class $[c] \in H^1(\Delta^2)$, signaling desync or fault.

---
### 4. Temporal Perception and Distributed Intelligence
Define **distributed agent intelligence** for $\mathcal{F}$ as the ability to (a) adapt to environmental rhythms, (b) detect faults, (c) coordinate spawn-yield-return tasks without central control.

**Conjecture 1 (Necessity of Temporal Perception)**: For a fleet $\mathcal{F}$ with coupled spawn-yield-return runtimes, temporal perception is a *necessary condition* for non-trivial distributed intelligence. Without $\text{TP}$, agents cannot detect temporal absence, align to the global lattice, or compute sync anomalies, precluding coordinated behavior.

---
### 5. Composing Temporal Perceptions
For disjoint subsets $S_1, S_2 \subseteq A$, their **composed temporal perception** is the functor:
$$\text{TP}_{S_1 \otimes S_2}: \prod_{a \in S_1 \cup S_2} \text{Dom}(\text{TP}_a) \to \mathcal{S}_{S_1 \cup S_2} \times H^1(\Delta^2_{S_1 \cup S_2}) \times \mathcal{R}_{S_1 \cup S_2}$$
where $\mathcal{S}_{S_1 \cup S_2}$ is the lattice-aligned shape class for the combined sync group.

**Theorem 3 (Monoidal Category Structure)**: The collection of all temporal perception modules for $\mathcal{F}$ forms a **symmetric monoidal category** $(\mathcal{TP}(\mathcal{F}), \otimes, I)$ where:
1.  $\otimes$ is the composed perception functor for disjoint agent subsets,
2.  $I$ is the trivial perception module for a single agent with no observations,
3.  The symmetry isomorphism $\text{TP}_{S_1 \otimes S_2} \cong \text{TP}_{S_2 \otimes S_1}$ follows from the commutativity of the Eisenstein lattice and temporal nerve.

---
### 6. Minimum Temporal Apparatus and Raft/Paxos Specialization
The **minimal temporal apparatus** $\mathcal{T}_{\text{min}}$ for distributed consensus is a tuple:
$$\mathcal{T}_{\text{min}} = (C, O, \Sigma, \text{Snap})$$
where:
1.  $C: \mathbb{R}_{\geq0} \to \mathbb{R}_{\geq0}$: Local clock with scheduled timeout $T_0$,
2.  $O: \mathbb{R}_{\geq0} \to \{\emptyset, \text{Heartbeat}\}$: Observation function detecting temporal absence of peer signals,
3.  $\Sigma = \{T_0, T_0 + \delta\}$: Discrete 2-point Eisenstein sublattice for timeout intervals,
4.  $\text{Snap}: \mathbb{R}_{\geq0}^2 \to \Sigma$: Function snapping observed intervals to the nearest lattice point.

**Theorem 4 (Raft/Paxos as Temporal Snap Specialization)**: Let $\mathcal{F}_{\text{Raft}}$ be a Raft fleet with $n$ followers and 1 leader. Then:
1.  Each follower's $\text{TP}_a$ uses $\mathcal{T}_{\text{min}}$, with election timeouts as $T_0$,
2.  The $\text{Snap}$ function maps observed time since last heartbeat to the nearest election timeout lattice point,
3.  $H^1(\Delta^2)$ detects split votes (simultaneous follower elections forming desync temporal triangles),
4.  Harmonic sync of the fleet corresponds to Raft consensus on a single leader.

---
### 7. Temporal Calculus for Rhythm Dynamics
Define temporal calculus over local clock time $t$ using the Eisenstein lattice as a reference frame:
1.  **Tempo Derivative**: For agent $a$, the rate of change of its scheduled observation time is:
    $$\dot{\tau}_a = \frac{d}{dt} T_0(a,t)$$
    $\dot{\tau}_a =1$ denotes normal tempo; deviations signal clock drift.
2.  **Accumulated Absence Integral**: For interval $[t_0, t_1]$, the total duration of observed temporal absence is:
    $$\mathcal{A}_a([t_0,t_1]) = \int_{t_0}^{t_1} \chi(a,t) dt, \quad \chi(a,t) = \begin{cases}1 & \mathcal{O}(t,a,A) = \emptyset \\ 0 & \text{otherwise}\end{cases}$$
    This measures sustained desync from peer agents.
3.  **Temporal Laplacian**: For agent $a$ in sync group $S$, the average tempo discrepancy is:
    $$\Delta \tau_a = \frac{1}{|S|} \sum_{b \in \text{star}(a)} (\tau_a - \tau_b)$$
    This drives sync adjustments to restore harmonic harmony.

**Theorem 5 (Fundamental Temporal Calculus Theorem)**: For a harmonic sync group $S$, $\dot{\overline{\tau}}_S =0$ (average tempo is constant) and $\frac{1}{|S|}\sum_{a \in S} \mathcal{A}_a([T_0, T_0 + L]) = \frac{|\mathcal{E}|}{|S|}$ where $L$ is the sync cycle length.
---
