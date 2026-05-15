# Analysis: The Aham Brahmasmi Approach — Hebbian AGI

## Source
Author: Jayan ("Jayan Solved AGI"), YouTube channel 1.75K subs
URL: superintelligencetoken.com
Date: Blog updated through 2023

## Core Claim
Unsupervised Hebbian learning in a large SNN (spiking neural network) with no objective function is sufficient for AGI. The mechanism: "relax when perceiving novelty, act when you don't." No backprop, no loss function, no reward signal.

## What's Actually Proposed
1. **Architecture**: 500K neurons, each connected to 5,000 others (random topology). Input/output devices connected randomly.
2. **Learning rule**: Hebbian (fire together → wire together) + weight decay (anti-Hebbian for non-firing pairs).
3. **Key mechanism**: Repeated inputs strengthen pathways → activation reaches output faster → action. Novel inputs travel fresh weak pathways → delayed output → "suspension of action" = attention/engagement.
4. **Emergent behavior**: Novelty-seeking, obstacle avoidance, associative memory, planning, classification of good/bad — all claimed to emerge from Hebbian dynamics alone.
5. **Prototype**: 500K neuron maze runner.

## Assessment

### Interesting Intuitions (not wrong in principle)
1. **"Novelty suspends action"** — This is real in neuroscience. Predictive coding models (Friston) formalize exactly this: prediction errors (novelty) suppress motor output until resolved. Orienting responses work this way.
2. **Hebbian learning creates associative structure** — True. Hopfield networks, reservoir computing, and self-organizing maps all demonstrate this.
3. **No explicit objective function needed** — Partially true. Curiosity-driven RL (Pathak et al. 2017) and unsupervised prediction show that intrinsic motivation can replace external reward. But these systems still have *implicit* objectives (minimize prediction error).
4. **Scale matters** — Starting with 100B neurons is different from evolving from 1. Fair point.

### Critical Problems

**Problem 1: No formal model.** Six "formulas" are mentioned but never written out. We get descriptions like "FORMULA 1: the connection weights increase" — no actual equations. This makes the proposal untestable.

**Problem 2: The novelty mechanism is underspecified.** The claim: "novel inputs travel different paths → slower → suspension of action." But HOW does the network know a path is "new"? In a Hebbian network, every input pattern activates SOME path. The distinction between "habituated path" and "novel path" requires a specific architectural mechanism (e.g., lateral inhibition, adaptation currents, synaptic depression). None are specified.

**Problem 3: The action selection problem is handwaved.** "Keep acting until something impactful happens" — but how does the system evaluate whether its action was impactful? That's an objective function by another name. The author says "it's subjective, can't be formalized" — but then the system can't learn, because learning requires a signal.

**Problem 4: No comparison to existing work.** This exact idea (Hebbian + novelty = emergent intelligence) has been formalized and tested by:
- **Reservoir computing** (Maass et al., Jaeger) — Hebbian-like dynamics in recurrent networks
- **Curiosity-driven RL** (Pathak et al., Intrinsic Curiosity Module) — novelty as intrinsic reward
- **Active inference** (Friston) — formal Bayesian framework where agents minimize surprise
- **Self-organizing maps** (Kohonen) — Hebbian-like topology formation
- **Liquid state machines** (Maass et al.) — spiking networks with readout training

The author reinvents concepts from all of these without citation or acknowledgment.

**Problem 5: The prototype is trivial.** A 500K neuron maze runner that avoids obstacles via Hebbian conditioning is a student project, not AGI evidence. Braitenberg vehicles from the 1980s did this with simpler mechanisms.

**Problem 6: The "just scale it" argument.** "Start with 100B neurons" — but the author hasn't demonstrated that the mechanism works at 500K. Scaling an unproven mechanism doesn't make it work better; it makes it fail at greater expense.

### Relevance to Our Work

**The interesting connection:** Our Vocabulary Rerouting findings show something structurally similar to what Jayan describes:

- **Domain vocabulary = novelty signal**: Low-frequency domain terms (Eisenstein) act like novel inputs in Jayan's model — they suspend the "habituated" computation pathway
- **Familiar vocabulary = fast pathway**: Common terms follow well-worn neural paths → quick, correct computation
- **Formula selection = pathway selection**: Study 44 showed vocabulary literally selects which computation the model performs

But our data shows the OPPOSITE of what Jayan claims. In transformers:
- Novel/low-frequency vocabulary does NOT suspend action — it SELECTS a wrong action (formula override)
- The "fast pathway" (familiar vocabulary) produces CORRECT computation, not automatic action
- Scale does NOT solve the problem (405B fails worse than smaller Seed-2.0)

### Verdict

**This is not publishable research.** It's a blog post with interesting but underspecified intuitions. The core insight (Hebbian + novelty → emergent intelligence) has been better formalized by Friston, Pathak, and others. The prototype is trivial. No formal model exists.

**The one redeeming feature**: Jayan correctly identifies that current deep learning's reliance on explicit objective functions is a fundamental limitation. This is widely acknowledged (Yann LeCun's JEPA, Friston's active inference, Schmidhuber's RNN-based curiosity). But acknowledging a problem isn't the same as solving it.

### What Would Make This Real
1. Write actual equations for the six "formulas"
2. Benchmark against curiosity-driven RL on a standard task
3. Show scaling behavior (does 5M neurons do anything 500K doesn't?)
4. Compare to reservoir computing and liquid state machines
5. Publish on arxiv with proper citations
