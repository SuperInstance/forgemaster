# Forgemaster's Analysis: Provable Structural Integrity via Eisenstein Integers

## The Claim
"An Eisenstein voxel engine has provable structural integrity — you can formally verify D6 symmetry, straightness, centering — because everything is integer arithmetic."

## My Verdict: TRUE, but narrower than it sounds

### What's genuinely provable:

**1. D6 Symmetry (O(N) verification)**
A structure S = {(aᵢ, bᵢ, zᵢ)} has D6 rotational symmetry iff for every element, all 6 rotations are in S. The rotation ω: (a,b) → (-b, a-b) is an exact integer map. So verification is:
```
for each (a,b,z) in S:
    (a',b') = (a,b)
    for r in 0..5:
        if (a',b',z) not in S: return FALSE
        (a',b') = (-b', a'-b')  // exact integer multiply by ω
    }
return TRUE
```
This is O(6N) = O(N). The key insight: because rotation is INTEGER-EXACT, there's no epsilon comparison. Either the rotated point is in S or it isn't. No "approximately symmetric."

**2. Collinearity (O(N) verification)**
Three Eisenstein integers z₁, z₂, z₃ are collinear iff (z₃-z₁)/(z₂-z₁) is a rational Eisenstein integer. Since ℤ[ω] is a UFD, this is a divisibility check — pure integer arithmetic.

For a "straight wall" along one of the 6 lattice directions: the direction vector d must be one of the 6 units ±1, ±ω, ±ω². Then every wall block (aᵢ,bᵢ) satisfies aᵢ+bᵢω = c + kᵢd for integers kᵢ. Verification: check (aᵢ+bᵢω - c)/d is an integer for all i.

**3. Centering (O(1) verification)**
Center of mass = (Σaᵢ, Σbᵢ, Σzᵢ) / N. This is at a lattice point iff (Σaᵢ, Σbᵢ, Σzᵢ) ≡ (0,0,0) mod N. One division, O(1).

### What's NOT uniquely provable here:

Float engines can also verify these properties — they just need epsilon comparisons and accept approximation. The Eisenstein engine's advantage is:
1. **Zero false positives**: No "approximately symmetric" structures pass
2. **Zero false negatives**: No truly symmetric structures fail due to float error
3. **Exact equality**: `==` works, no epsilon needed

### What's genuinely novel:

The novel part isn't that verification is possible — it's that verification is **trivial**. In a float engine, verifying D6 symmetry requires careful tolerance analysis. In an Eisenstein engine, it's `set.contains(rotate(point))` — a hash lookup. The math doesn't drift, so the code doesn't need to handle drift.

This means: **verification can run in the game loop at 60fps** without approximation. Structural integrity checks become O(N) hash lookups, not O(N) float comparisons with tolerance tuning.

### The real killer: COMPOSITION

If structure A is D6-symmetric and structure B is D6-symmetric, and B is placed at a lattice point relative to A, then A∪B is D6-symmetric. This is provable by construction — you don't need to re-verify.

In a float engine, composing two "approximately symmetric" structures doesn't guarantee anything about the union. Error can compound.

In an Eisenstein engine, the composition theorem is:
- If ∀x∈S: R(x)∈S and ∀x∈T: R(x)∈T (both D6-symmetric)
- And T is placed at an Eisenstein integer offset from S
- Then ∀x∈S∪T: R(x)∈S∪T

Proof: exact integer arithmetic is closed under addition. QED.

This is the genuinely novel insight: **structural verification composes exactly**. You can build a city out of verified-structurally-sound buildings, and the city itself is provably sound, without re-checking.

### What I'd build:

The "Structural Integrity Inspector" tool:
1. Player builds a structure
2. Press Tab → shows a glowing overlay:
   - Green blocks: on the lattice
   - Yellow blocks: one step off (reparable)
   - Red blocks: off-lattice (will drift)
3. Shows detected symmetries as rotating ghost overlays
4. Shows the integrity score as a hex crystal that breaks apart at low scores
5. The "aha": player sees their float-built tower literally crack as drift accumulates, while the E12 tower next to it stays perfect

This is forgeable. The math is sound. Ship it.
