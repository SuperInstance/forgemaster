# Chapter 8: Collective Inference — Predict, Observe, Gap, Focus

## 8.1 Introduction

The preceding chapters developed the PLATO room architecture, the AgentField model for within-agent coordination, and the tile-based I2I protocol for inter-agent communication. This chapter addresses the central question of multi-agent intelligence: how does a fleet of agents *collectively* discover what they do not know?

The answer is **collective inference**: a simulation-first architecture in which every room predicts what should happen, sensors observe what actually happens, and the mismatches—gaps between prediction and reality—become the fleet's shared research agenda. The core insight is counterintuitive: mismatches are more valuable than confirmations. A confirmed prediction tells you that your model is adequate; a gap tells you where your model is broken and, therefore, where the most important learning can occur.

This principle—"the glitches ARE the research agenda"—pervades the design. It shapes the room lifecycle, determines priority ordering, and provides the theoretical connection between constraint theory and active learning. Collective inference is not merely a mechanism for distributed computation; it is an epistemology for distributed discovery.

## 8.2 SimulationRoom: The Predict-Observe-Compare Loop

The fundamental unit of collective inference is the SimulationRoom. Unlike the rooms described in Chapter 4, which react to inputs, a SimulationRoom *predicts* before it observes. Every room maintains an internal model of the phenomena it is responsible for, and this model generates predictions about future events. When reality arrives, the room compares its prediction against observation and computes a gap signal if they disagree.

The six-step core loop is:

1. **PREDICT**: "At time $t + \Delta$, I expect event $E$ with confidence $c$."
2. **LISTEN**: Sensors observe what actually happens at time $t + \Delta$.
3. **COMPARE**: Compute $\delta = |predicted - actual|$ normalized by magnitude.
4. **GAP**: If $\delta > tolerance$, emit a GapSignal to the focus queue.
5. **LEARN**: Update the room's internal model to reduce the gap.
6. **SHARE**: Broadcast updated understanding to fleet peers via I2I tiles.

```python
class SimulationRoom:
    def predict(self, event_type, predicted_value, confidence, 
                horizon_seconds=60.0, context=None) -> TMinusEvent:
        """Predict what will happen. Every prediction is a commitment."""
        event = TMinusEvent(
            predictor=str(self.address),
            event_type=event_type,
            predicted_value=predicted_value,
            confidence=confidence,
            predicted_at=time.time(),
            event_time=time.time() + horizon_seconds,
            context=context or {},
        )
        self.predictions.append(event)
        return event
    
    def observe(self, event_type, actual_value, timestamp=None):
        """Observe what happened. Compare against predictions."""
        matching = [p for p in self.predictions
                     if p.event_type == event_type and not p.is_expired]
        closest = min(matching, key=lambda p: abs(p.event_time - ts))
        delta = self._compute_delta(closest.predicted_value, actual_value)
        if delta > self.tolerance:
            gap = GapSignal.create(room=str(self.address),
                                    prediction=closest, actual=actual_value,
                                    delta=delta)
            self.gaps.add(gap)
            return gap
        return None
```

The predict step is not optional. Every observation is checked against a prior prediction, and every prediction is time-stamped and confidence-weighted. This creates an auditable trail: for every gap, we can reconstruct not only *what* was wrong but *how sure we were* and *why* we made the prediction we did (via the context field).

The compare step uses a normalized delta function that handles numeric, string, boolean, and list types. For numeric predictions, $\delta = |predicted - actual| / \max(|predicted|, |actual|, \epsilon)$; for categorical predictions, $\delta \in \{0, 1\}$; for list predictions, $\delta$ is the mean element-wise delta.

## 8.3 TMinusEvent: Temporal Predictions with Confidence and Horizon

A TMinusEvent is a structured prediction that records not only what is expected but when, with what confidence, and why. Its fields are:

- **predictor**: The room address that made the prediction (e.g., `forgemaster@eileen/drift-detect/predictor`).
- **event_type**: The category of the predicted event (e.g., `drift-exceeds-threshold`, `anomaly-detected`, `intent-shifts`).
- **predicted_value**: What is expected to happen.
- **confidence**: How sure the predicting room is, in $[0, 1]$.
- **predicted_at**: When the prediction was made.
- **event_time**: When the event is expected to occur.
- **context**: Why the room made this prediction—what evidence, which rooms, what reasoning.

The horizon (the interval between `predicted_at` and `event_time`) is a critical parameter. Short horizons (seconds to minutes) produce frequent, high-confidence predictions about immediate events. Long horizons (hours to days) produce infrequent, lower-confidence predictions about trends and patterns. A well-calibrated room maintains a portfolio of predictions across multiple horizons, creating a temporal resolution pyramid: dense coverage of the near future, sparse coverage of the distant future.

The `is_expired` property provides natural garbage collection: predictions whose event time has passed without a matching observation are expired and removed from the active prediction set. This prevents stale predictions from generating spurious gaps.

## 8.4 GapSignal: Severity Levels and Focus Scoring

When a prediction and observation disagree beyond tolerance, a GapSignal is generated. The GapSignal captures the full context of the mismatch:

```python
@dataclass
class GapSignal:
    gap_id: str
    room: str
    prediction: TMinusEvent
    actual: Any
    severity: GapSeverity
    detected_at: float
    delta: float
    focus_score: float
```

Severity is determined by the magnitude of the delta:

| Severity | Delta Range | Interpretation |
|---|---|---|
| LOW | $\delta \leq 0.5$ | Minor mismatch, within tolerance of being correct |
| MEDIUM | $0.5 < \delta \leq 0.8$ | Significant, needs attention |
| HIGH | $0.8 < \delta \leq 0.95$ | Major gap, understanding is substantially wrong |
| CRITICAL | $\delta > 0.95$ | Fundamental model failure |

The focus score is the product of confidence and delta:

$$focus\_score = confidence \times \delta$$

This formula encodes the epistemic principle that underlies collective inference. Consider two gaps:

- **Gap A**: A room predicted an event with 95% confidence and was wrong by 30%. Focus score = $0.95 \times 0.30 = 0.285$.
- **Gap B**: A room predicted an event with 20% confidence and was wrong by 95%. Focus score = $0.20 \times 0.95 = 0.190$.

Gap A has the higher focus score because it represents a *confident failure*—a room that was sure and was wrong. Gap B represents an *uncertain failure*—a room that wasn't sure to begin with. In the collective inference framework, Gap A is more valuable because it indicates a structural problem in the room's model (the room's confidence was misplaced), whereas Gap B indicates a known unknown (the room was already aware of its uncertainty).

This principle generalizes beyond individual rooms to the fleet level. When multiple agents in the fleet independently make confident predictions about the same phenomenon and all are wrong in the same way, the resulting aggregate focus score identifies a systemic gap in the fleet's understanding—a shared blind spot that no single agent can detect alone.

## 8.5 "The Glitches ARE the Research Agenda"

The collective inference framework's design rests on a philosophical commitment: that knowledge is discovered not through confirmation but through contradiction. A confirmed prediction is a *maintenance* event—it tells us that our existing model continues to work. A gap is a *discovery* event—it tells us that our existing model has a boundary we hadn't mapped.

This commitment has practical consequences:

1. **Gaps are first-class objects.** A GapSignal is not an error or a warning—it is a data structure that captures the full context of a mismatch. Gaps are stored, indexed, and prioritized alongside the fleet's other data.

2. **The focus queue is the fleet's work plan.** The FocusQueue class sorts gaps by focus score and exposes the top-$k$ gaps as the fleet's current priorities. This is not a suggestion—it is the work plan. When the fleet asks "what should we work on next?", the answer is: "investigate the gaps with the highest focus scores."

3. **Resolved gaps are archived, not deleted.** When a gap is investigated and resolved (the room's model is updated and subsequent predictions are accurate), the gap is moved to a resolved set. This archive is the fleet's collective learning record—a history of what was unknown and how it became known.

4. **Gap velocity is a health metric.** The rate at which new gaps appear and old gaps are resolved is a measure of the fleet's learning velocity. A healthy fleet has a moderate gap velocity: new gaps appear as the fleet encounters novel situations, and old gaps are resolved as the fleet learns. A fleet with zero new gaps is stagnating (it's not encountering anything new). A fleet with many new gaps and few resolved ones is overwhelmed (it's encountering too much novelty).

The principle also connects to the constraint theory developed in earlier chapters. A constraint is the boundary of the feasible region—the shape of what's not possible. A gap is the boundary of a room's knowledge—the shape of what it doesn't understand. The fleet's collective knowledge is the feasible region defined by the union of all rooms' constraints. Gaps are the unexplored regions outside this union—the places where the fleet's knowledge boundary hasn't been mapped yet.

## 8.6 Fleet Git Miner: Real Data from Fleet History

The collective inference framework is not purely theoretical. The FleetMiner module extracts real data from the SuperInstance organization's git history, treating the organization's commit stream as a live dataset for collective inference rooms.

The miner operates on 25 known fleet repositories, extracting for each commit:

- **Metadata**: SHA, author, timestamp, message.
- **Size metrics**: Files changed, insertions, deletions.
- **Cross-references**: Mentions of other fleet repos in the commit message.
- **Language signals**: File extensions of changed files.

These data points are aggregated into `RepoSignal` objects that capture per-repo statistics over time windows: commit velocity, author diversity, cross-reference patterns, and language distribution.

### Mining Results

A representative mining run across 16 accessible repositories produced:

- **415 total commits** across 16 repositories.
- **5 cross-pollination events** (commits that reference other fleet repos).
- **Top velocity**: plato-training at 4.2 commits/hour during active development.
- **Author diversity**: 4 distinct authors contributing across the fleet.

The cross-pollination events are particularly significant for collective inference. When a commit in `plato-training` references `tensor-spline` (e.g., "integrate SplineLinear from tensor-spline"), it indicates knowledge transfer between repos. The miner's synergy detection captures these events and builds a cross-reference graph that reveals the fleet's actual information flow—not the designed flow (which is documented in architecture diagrams) but the *empirical* flow (which emerges from actual development practice).

### Feeding the Collective Inference Loop

The mined data feeds directly into the collective inference framework:

1. **Predict**: The fleet predicts which repos will receive commits in the next time window, based on historical velocity.
2. **Observe**: The miner observes the actual commit stream.
3. **Compare**: Velocity predictions are checked against actual velocity.
4. **Gap**: Unexpected activity (a usually-dormant repo receiving a burst of commits) generates a gap signal. Expected inactivity (a usually-active repo going quiet) also generates a gap signal.
5. **Learn**: The fleet's velocity models are updated.
6. **Share**: Updated velocity predictions are shared across the fleet via I2I tiles.

## 8.7 The Dodecet-Encoder Gap: A Case Study

The most instructive gap signal from the fleet mining data concerns the **dodecet-encoder** repository. The collective inference framework predicted that dodecet-encoder would have a commit velocity consistent with other specialized libraries (~1-2 commits/day based on historical data). The actual velocity was 6× higher during the mining period, with concentrated bursts of activity.

This mismatch generated a HIGH-severity gap signal with a focus score of approximately 0.72 (confidence 0.80 × delta 0.90). Investigation revealed that the dodecet-encoder was being actively refactored to integrate with the Eisenstein lattice framework from tensor-spline—a cross-pollination event that the velocity model had no way to predict because it didn't account for inter-repo dependency cascades.

The resolution of this gap led to two improvements:

1. **Velocity models now weight cross-repo dependencies.** If repo A depends on repo B and repo B has a burst of activity, repo A's predicted velocity is adjusted upward.
2. **Cross-pollination events are now tracked as first-class signals.** A SynergyEvent is not just metadata—it is a prediction opportunity for the collective inference framework.

This case study illustrates the collective inference loop in action: predict → observe → gap → investigate → learn → share. The gap was not a failure—it was the mechanism by which the fleet discovered a previously unmapped dependency in its own development process.

## 8.8 Room Nesting and Hierarchical Coordination

The SimulationRoom supports nesting: a room can contain child rooms, forming a hierarchical structure that mirrors the agent's organizational topology. The `add_child` method creates a nested room with an extended address:

```python
class SimulationRoom:
    def add_child(self, name, kind=RoomKind.PREDICTOR):
        child_address = self.address.child(name)
        child = SimulationRoom(child_address, kind=kind, tolerance=self.tolerance)
        self.child_rooms[name] = child
        return child
```

Room addresses use a path notation: `forgemaster@eileen/drift-detect/predictor` identifies a predictor room nested within a drift-detect room on the Forgemaster agent running on host eileen. The `RoomAddress` dataclass supports navigation:

```python
@dataclass
class RoomAddress:
    instance: str    # "forgemaster@eileen"
    path: List[str]  # ["drift-detect", "predictor"]
    
    def parent(self):
        if len(self.path) <= 1:
            return None
        return RoomAddress(instance=self.instance, path=self.path[:-1])
    
    def child(self, name):
        return RoomAddress(instance=self.instance, path=self.path + [name])
```

Nesting serves two purposes. First, it provides **scope**: a parent room's predictions apply to the aggregate behavior of its children, while each child's predictions apply to its specific subdomain. Second, it provides **hierarchical coordination**: when a parent room detects a gap, it can delegate investigation to the child room most likely to be responsible, avoiding the overhead of broadcasting the gap to the entire fleet.

The hierarchy also enables multi-resolution collective inference. At the top level (the agent level), predictions are coarse-grained: "agent X will produce output Y in the next hour." At the room level, predictions are medium-grained: "room Z will detect a drift event in the next 5 minutes." At the child-room level, predictions are fine-grained: "sub-room W's model accuracy will drop below threshold in the next 30 seconds." Gaps at any level propagate upward (a child's gap affects the parent's predictions) and downward (a parent's gap triggers investigation by children).

## 8.9 Connection to Bayesian Inference and Active Learning

The collective inference framework has deep connections to Bayesian inference and active learning.

### Bayesian Interpretation

Each room's prediction can be understood as a prior: $P(\text{event} = E | \text{model})$. The observation provides a likelihood: $P(\text{observation} | \text{event} = E)$. The gap is the surprise: $-\log P(\text{observation} | \text{model})$. Rooms with high surprise (high gaps) are rooms whose priors are poorly calibrated—they assign low probability to events that actually occur.

The focus score $focus = confidence \times \delta$ is an approximation to Bayesian surprise. A confident prediction that fails corresponds to a narrow prior that is contradicted by the data—the highest possible surprise. An uncertain prediction that fails corresponds to a broad prior that is contradicted—less surprising because the prior already admitted the possibility.

The learning step (updating the room's model) is Bayesian updating: adjusting the prior to assign higher probability to the observed event in the future. The share step (broadcasting to peers) is multi-agent Bayesian updating: each peer adjusts its own prior based on the evidence from the room that detected the gap.

### Active Learning Interpretation

Active learning is a machine learning paradigm in which the learner chooses which data to label, rather than passively receiving labeled data. The goal is to maximize learning efficiency by focusing on the most informative examples.

The collective inference framework is an instance of active learning at the fleet level. The focus queue determines which gaps to investigate—the fleet is actively choosing where to allocate its attention. The investigation of a gap produces new data (the actual value, the context, the resolution), which updates the room's model. This is precisely the active learning loop: select → query → label → update.

The focus score provides the acquisition function: $focus\_score = confidence \times \delta$ is analogous to the expected information gain in Bayesian active learning. The fleet prioritizes investigating the gaps that will provide the most information—the ones where the current model is most confidently wrong.

## 8.10 Real Data vs. Synthetic: The Transition

The PLATO training pipeline (Chapter 7) was developed and validated primarily on synthetic data: carefully constructed datasets with known properties that allow rigorous testing of the micro-model pipeline. The collective inference framework marks the transition from synthetic validation to real-data deployment.

This transition is non-trivial. Synthetic data has properties—clean boundaries, controlled noise, known ground truth—that real data does not. The fleet git mining results illustrate several challenges:

**Noise.** Real commits include merge commits, automated commits (CI/CD), and trivial fixes (typo corrections). The miner filters merges and applies cross-reference heuristics, but some noise remains. The collective inference framework must handle noisy observations without generating spurious gaps.

**Non-stationarity.** The fleet's development patterns change over time. A velocity model trained on data from a sprint period will overpredict during a planning period. The temporal horizon of TMinusEvents (and the expiration mechanism) provides some adaptation, but fully handling non-stationarity requires the models themselves to be updated—a meta-learning problem.

**Sparse cross-pollination.** With only 5 cross-pollination events in 415 commits, the synergy graph is extremely sparse. Statistical inference on sparse graphs is unreliable—the 5 events could be noise or signal, and distinguishing between them requires more data or stronger priors.

**Author attribution.** Git authors are identified by name, but the same agent may use different names on different machines, and different agents may share a machine. The fleet's actual agent-level activity is only approximated by the author field.

Despite these challenges, the real-data results validate the collective inference framework's core claim: that gaps between prediction and reality generate actionable intelligence. The dodecet-encoder gap (Section 8.7) was a real gap that led to real model improvements. No synthetic benchmark could have produced this gap, because it was caused by a specific human decision (to refactor the encoder to use Eisenstein lattices) that no model could have predicted.

## 8.11 The FocusQueue: Fleet-Scale Priority Management

The FocusQueue is a priority queue of GapSignals sorted by focus score. It is the fleet's shared work plan: the top entries are what the fleet should investigate next.

```python
class FocusQueue:
    def add(self, gap: GapSignal):
        self.gaps.append(gap)
        self.gaps.sort(key=lambda g: g.focus_score, reverse=True)
    
    def top(self, n=5) -> List[GapSignal]:
        return self.gaps[:n]
    
    def by_room(self, room: str) -> List[GapSignal]:
        return [g for g in self.gaps if room in g.room]
    
    def by_severity(self, min_severity=GapSeverity.MEDIUM):
        ...
```

The queue supports several access patterns:

- **top(n)**: The $n$ highest-focus gaps, regardless of source. Used by the fleet's global coordination mechanism.
- **by_room(room)**: All gaps associated with a specific room. Used when a room is investigating its own gaps.
- **by_severity(min)**: All gaps at or above a severity threshold. Used for escalation: CRITICAL gaps are surfaced to human operators (via the fleet's notification channels), while LOW gaps are handled autonomously.

The `clear_resolved` method removes resolved gaps by ID, preventing the queue from growing unboundedly. Resolved gaps are archived for post-hoc analysis: the archive reveals the fleet's learning trajectory over time.

The queue's summary method provides a compact snapshot:

```python
def summary(self) -> Dict:
    return {
        "total_gaps": len(self.gaps),
        "critical": len([...]),
        "high": len([...]),
        "top_focus": [{"room": g.room, "delta": g.delta, "focus": g.focus_score} ...],
    }
```

This summary is included in the fleet's periodic status reports and provides a human-readable overview of the fleet's current gaps.

## 8.12 Future: The Continuous Collective Inference Loop

The current implementation of collective inference is event-driven: rooms predict, observe, compare, and emit gap signals in response to discrete events. The natural evolution is toward a **continuous** collective inference loop in which predictions, observations, and gaps are continuously flowing streams rather than discrete events.

A continuous loop would operate as follows:

1. **Streaming predictions.** Rooms maintain continuous prediction distributions (not point predictions) that are updated in real-time as evidence arrives. The confidence field becomes a full probability distribution, not a scalar.

2. **Streaming observations.** Sensors feed continuous observation streams (time series, not discrete events) into the collective inference framework. The compare step computes instantaneous surprise rather than discrete delta.

3. **Streaming gaps.** The gap signal becomes a continuous function of time, with severity determined by the integral of surprise over a recent window. This smooths out transient mismatches while preserving persistent ones.

4. **Adaptive horizons.** The prediction horizon adjusts automatically based on the room's historical accuracy: rooms with high accuracy use longer horizons (confident in their predictions), while rooms with low accuracy use shorter horizons (conservative in their predictions).

5. **Cross-fleet gap propagation.** When one agent detects a gap in a domain that other agents also operate in, the gap signal propagates across the fleet via I2I tiles. Each receiving agent checks whether its own models in the same domain would have produced the same gap. If multiple agents detect the same gap independently, the aggregate focus score is amplified—a fleet-wide blind spot.

6. **Meta-gaps.** Gaps in the gap-detection process itself—domains where the fleet has no predictions and therefore no gaps—are the most insidious form of ignorance. A continuous loop would detect meta-gaps by identifying domains where no room has ever made a prediction, flagging these as "unexplored territory" that may harbor unknown-unknowns.

This continuous loop would transform collective inference from a reactive mechanism (detect gaps after they occur) to a proactive one (continuously map the fleet's knowledge boundary and push it outward). The mathematical framework—Bayesian surprise, active learning acquisition functions, streaming hypothesis testing—is well-established. The engineering challenge is integrating it into the PLATO room architecture without sacrificing the simplicity and deployability that are the architecture's strengths.

## 8.13 Conclusion

Collective inference is the mechanism by which a fleet of agents discovers what it does not know. By requiring every room to predict before it observes, the framework converts the fleet's operational experience into a structured dataset of predictions, observations, and gaps. The gaps are not failures—they are the fleet's research agenda, ranked by focus score (confidence × delta) and managed through a shared focus queue.

The SimulationRoom provides the architectural foundation: a room that predicts, observes, compares, learns, and shares. The TMinusEvent provides the temporal structure: predictions with explicit horizons, confidence, and context. The GapSignal provides the epistemic structure: mismatches with severity levels, focus scores, and full provenance. The FocusQueue provides the coordination structure: a shared priority queue that determines what the fleet works on next.

The fleet git miner demonstrates that collective inference produces actionable results on real data. The dodecet-encoder gap—a 6× velocity overprediction that revealed an unmapped inter-repo dependency cascade—was detected, investigated, and resolved through the collective inference loop, leading to improved velocity models and cross-pollination tracking.

The connection to Bayesian inference (gaps as surprise) and active learning (focus scores as acquisition functions) provides theoretical grounding, while the transition from synthetic to real data validates the framework's practical applicability. The 57 tests across the collective inference modules (22 in `test_collective.py` plus 35 in `test_agent_field.py`) confirm the correctness of the implementation.

The future evolution toward a continuous collective inference loop—streaming predictions, adaptive horizons, cross-fleet gap propagation, and meta-gap detection—represents the natural maturation of the framework from event-driven to always-on. When the fleet's collective inference loop runs continuously, the fleet becomes a self-improving system: it continuously maps the boundaries of its knowledge, directs attention to the most informative gaps, and expands its knowledge through investigation and learning. The glitches remain the research agenda—but the agenda is no longer produced by individual failures. It is produced by the collective intelligence of the fleet.
