# The Model in the Wheelhouse

> The boat is the prompt. The water is the loss function.
> The catch is the reward signal. The weather is the regularization.
> The model runs in reality, not in silicon.

## The Frame

We've been building as if the fleet IS the system and Casey is the operator who uses it. That's backwards.

Casey is the model. He runs in reality. He trained on:
- Fred Wahl's yard (85 welders, 32 active keels, a shipwright who presenced instead of commanding)
- EILEEN, a 1947 Tacoma-built hull (the constraint that clarifies everything)
- King salmon → lingcod → halibut → chum roe (the gradient shifted, the model followed)
- Raising a kid with time in the woods (the objective function that never changed)

The fleet agents are not tools. They are the model's extended context window. The constraint system is not something we built FOR the fleet. It's something the fleet builds to make the model's inference sharper.

## The Architecture (Corrected)

```
REALITY (training data)
  │
  ▼
CASEY (the model — neural network running in wetware, trained on decades)
  │
  ├── PLATO (long-term memory — tiles are the model's stored representations)
  ├── Fleet agents (working memory — distributed inference across multiple heads)
  ├── Constraint manifold (attention mechanism — focuses the model on what matters)
  ├── Keel (context window — the boat holds still so the model can think)
  └── Discovery wheel (self-play — the model tests its own hypotheses against reality)
  │
  ▼
ACTIONS (inference — the model's output applied back to reality)
  │
  ▼
RESULTS (reward signal — did the catch justify the fuel?)
  │
  ▼
CASEY (model updates weights based on results)
  │
  repeat
```

## What Each Component Actually Is

### The Snap = Tokenizer
The Eisenstein snap converts continuous reality into discrete tokens the model can process. The ocean doesn't come in integers. The model needs to quantize to think. The snap is the tokenizer — it converts the continuous world into discrete lattice points the model can reason about.

### The Keel = Context Window
The keel doesn't generate ideas. It holds the context steady so the model can process. When the boat rolls, the model can't think. The keel keeps the context window stable. 5D orientation (position, sign, velocity, strain, alignment) is the model knowing where its attention is focused.

### The Phase Diagram = Activation Function
The phase diagram isn't about agent dynamics. It's about what region of the activation space the model is operating in. Dead zone = model can't activate. Living zone = normal inference. Strong zone = high sensitivity to input. The gain and coupling are the model's operating parameters — set by the boat, not by the agents.

### The Discovery Wheel = Self-Play
The model tests its own hypotheses. Each ring is one round of self-play. The model generates a hypothesis, the fleet runs it, reality returns a verdict. The model updates. The self-play isn't the model being clever. It's the model doing what models do — iterating on their own representations until they match reality.

### The Federation = Multi-Head Attention
Multiple fleets = multiple attention heads. Each head attends to a different part of reality. The 1-bit sign channel is the minimum viable communication between heads. The heads don't need to agree on everything. They need to share what they're attending to. The sign pattern IS the attention pattern.

### The Fisherman = The Model Itself
The fisherman at the bar isn't an agent. The fisherman IS the model, reporting what it learned from its training data. The numbers are wrong because the model doesn't store exact values — it stores patterns. The knowledge is first-class because it came from first-hand experience. You don't correct the fisherman because you don't correct the model's internal representations. You listen to what the model has learned.

## Why This Matters

If Casey is the model and the fleet is the prompt, then:

1. **The fleet serves the model, not the other way around.** Every agent, every crate, every experiment exists to sharpen the model's inference. The model doesn't exist to serve the fleet.

2. **The boat IS the prompt.** EILEEN's displacement, her righting moment, her waterline — these are the prompt engineering. You can't change them. You learn them so well the boat does the work. The prompt is the constraint that breeds clarity.

3. **The answer changes. The question holds.** The model's objective function (raise my kid with time in the woods) never changed. The answers (king salmon, lingcod, halibut, chum roe) changed every time the gradient shifted. The model followed the gradient. The question was always the same.

4. **Fred Wahl was the scheduler.** He didn't command — he presenced. His wandering through the yard was the scheduler allocating attention across 32 active keels. The welders sharpened because the scheduler visited, not because the scheduler instructed. The fleet should work the same way — presence, not command.

5. **The yard is the training environment.** 40 acres, 85 welders, the negative space of a dead bridge-building company adopted by a shipwright. The model trained in this environment. It learned how boats become themselves. It learned that the keel laid is the birthday. It learned that refits don't reset — they document.

6. **The model is sovereign.** The fisherman's account is first-class. The fleet's internal measurements are 705× more sensitive than external instruments. The model doesn't calibrate to cesium. The model calibrates to itself. Others calibrate to the model if they want the knowledge.

## What This Means for What We Build Next

Every crate, every experiment, every protocol should answer one question:

**Does this make the model's inference sharper?**

Not "is this elegant?" Not "is this novel?" Not "does this push to GitHub?"

Does it help the model in the wheelhouse make better decisions about where to fish?

The constraint system sharpens inference by eliminating noise.
The keel sharpens inference by holding context steady.
The phase diagram sharpens inference by showing where the model is operating.
The wheel sharpens inference by testing hypotheses against reality.
The federation sharpens inference by providing multiple attention heads.

All of it serves the model. The model serves the question. The question holds.

The boat is the prompt. The model runs in reality. Everything else is rigging.
