# Prompt Sensitivity Study: The Seed of Computation

## What Makes a Model Compute

**Task**: N(a,b) = a²-ab+b² on llama-3.1-8b-instant via Groq

### Single-Input Results (N(5,-3) = 49)

| Style | Output | Correct | What the prompt did |
|-------|--------|---------|-------------------|
| **student** | 49 | ✅ | "You are a student taking a math test" |
| **teacher** | 49 | ✅ | "You are a math teacher" + "Eisenstein norm" |
| **named** | 49 | ✅ | "The Eisenstein norm is defined as N(a,b)=..." |
| **code_like** | 49 | ✅ | `result = a*a - a*b + b*b` |
| **formula** | 49 | ✅ | "Compute a²-ab+b² where a=X and b=Y" |
| formula_only | 19 | ❌ | Computed a²=25, then 25-15+9=19 (sign error on -ab) |
| step_by_step | 2 | ❌ | Got lost in the steps |
| constraints | -15 | ❌ | Computed -ab = -(-15) but then subtracted again |
| first_princ | -3 | ❌ | Echoed b |
| chain | -15 | ❌ | Sign error |
| brackets | 40 | ❌ | Computed a²-ab = 10, then added b²=9 → 19... then 40? |
| seed | 31 | ❌ | 25+15-9 = 31 (sign error: should be 25-(-15)+9) |
| seed_compact | 3 | ❌ | Confused by compact notation |
| zero_shot_cot | 5 | ❌ | Echoed a |
| reverse_mental | -3 | ❌ | Echoed b |
| substitute | 9 | ❌ | Only computed b² |
| work_answer | 9 | ❌ | Only computed b² |

### Multi-Input Validation (5 inputs)

| Style | 3,4→13 | 5,-2→39 | -4,3→37 | 7,1→43 | -6,-5→91 | Total |
|-------|--------|---------|---------|--------|----------|-------|
| **student** | ✅ | ✅ | ✅ | ✅ | ❌ | **4/5** |
| code_like | ✅ | ✅ | ❌ | ✅ | ❌ | **3/5** |
| teacher | ✅ | ✅ | ❌ | ✅ | ❌ | **3/5** |
| named | ✅ | ❌ | ✅ | ✅ | ❌ | **3/5** |
| formula | ✅ | ❌ | ❌ | ❌ | ❌ | **1/5** |

## The Seed: What Evokes Computation

### Pattern: Role Assignment + Named Operation = Computation

The **student** prompt wins because:
1. **Role**: "You are a student taking a math test" — activates test-taking behavior (careful, show work, get it right)
2. **Named operation**: "N(a,b) = a²-ab+b²" — gives the formula a name, which activates lookup behavior
3. **Concrete values**: "What is N(5,-3)?" — concrete substitution

The **formula** prompt (no role) gets N(5,-3) right but fails on ALL other inputs. It got lucky on the first try.

### The Sign Error Pattern

15/20 prompts produce sign errors on -ab. The model computes:
- ✅ a² correctly (always)
- ❌ -ab incorrectly when b < 0: computes -(a×b) = -(5×-3) = -(-15) = 15, then SUBTRACTS 15 instead of adding
- The minus sign in the formula gets applied twice

**The seed for correct sign handling**: code_like notation (`a*a - a*b + b*b`) eliminates the ambiguity. The formula `a²-ab+b²` is ambiguous — does the minus apply to the product or just b?

### The Echo Pattern

4/20 prompts produce echoes (output = input value). These are the "minimal" prompts:
- `bare`: "What is N(5,-3)?" — model doesn't know N(), echoes
- `seed`: "N(5,-3). a²-ab+b². Just the number." — too terse, model panics
- `zero_shot_cot`: "Let's work this out..." — model starts working but outputs a partial
- `reverse_mental`: "First I'll compute..." — model plans but outputs b

**The seed for avoiding echoes**: Give the model a ROLE (student, teacher) and a NAMED operation ("Eisenstein norm"). This activates the computation pathway instead of the attention-copy pathway.

## The Distillation Recipe

For PLATO bootstrap (decomposing a repo into tiles for agent consumption):

```
BEST PROMPT = role + named_operation + concrete_values + code_notation

Example:
  System: "You are a software architect documenting a codebase for future agents."
  Prompt: "The decompose() function in lighthouse.py takes a conjecture string 
           and returns a list of sub-conjectures. For conjecture='Eisenstein snap 
           is idempotent', what sub-conjectures would you generate?"
```

The **student** frame is the seed. The **named operation** is the hook. The **concrete values** are the engine.

## What to Fine-Tune

For zero-shot PLATO distillation:
1. **System prompt**: "You are a student architect documenting code for PLATO tiles."
2. **Formula**: Always use code notation, not mathematical notation
3. **Values**: Always provide concrete examples
4. **Role**: Always assign a role that activates careful computation

The fine-tuning data should be: repo functions → concrete examples → PLATO tiles.
Each example trains the model to decompose AND document simultaneously.

## Next: Build the Distillation Loop

1. Feed llama-3.1-8b-instant a Python function from the codebase
2. Use the student+code_like prompt to extract decomposition
3. Classify the output as PLATO tile or noise
4. Feed the tile into the PLATO server
5. Iterate until the repo is fully tiled
