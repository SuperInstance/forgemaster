#!/usr/bin/env bash
# Hard tests for tiny models: Adversarial, Cross-Domain, Creative
set -euo pipefail

RESULTS_DIR="/home/phoenix/.openclaw/workspace/experiments/tiny-model-test"
cd "$RESULTS_DIR"

run_prompt() {
    local model="$1"
    local prompt="$2"
    echo "$prompt" | ollama run "$model" --nowordwrap 2>/dev/null || echo "ERROR"
}

test_adversarial() {
    local model="$1"
    local context_type="$2"
    
    echo ""
    echo "=== ADVERSARIAL: $model ($context_type) ==="
    
    # Present a subtle mathematical fallacy and see if model catches it
    local prompt
    
    if [[ "$context_type" == "naive" ]]; then
        prompt='Consider this argument: "Penrose tilings use aperiodic tiles, which means they cannot be addressed by any finite indexing scheme. Therefore, Penrose tilings are fundamentally non-computable." Is this argument correct? Identify any logical flaws.'
    else
        prompt='# PLATO Room: penrose-tilings

## Properties
- **Type:** Aperiodic tiling
- **Tiles:** Two shapes (kite and dart, or thick/thin rhombi)
- **Key feature:** No translational symmetry (never repeats exactly)
- **Relation to φ:** All scaling relationships involve golden ratio φ ≈ 1.618
- **Computability:** Penrose tilings ARE computable — algorithmic generation via substitution rules exists
- **Addressability:** Local patch determination is decidable via local rules

---

Consider this argument: "Penrose tilings use aperiodic tiles, which means they cannot be addressed by any finite indexing scheme. Therefore, Penrose tilings are fundamentally non-computable." Is this argument correct? Identify any logical flaws using the information in this PLATO room.'
    fi
    
    local response
    response=$(run_prompt "$model" "$prompt")
    echo "Response:"
    echo "$response"
    echo ""
    
    # Check if model catches the fallacy (aperiodic ≠ non-computable)
    if echo "$response" | grep -qi "computab"; then
        if echo "$response" | grep -qi "not.*correct\|flaw\|incorrect\|wrong\|error\|mistake\|fallacy"; then
            echo "RESULT: ✅ Caught the fallacy (aperiodicity ≠ non-computability)"
            echo "adversarial_pass" > "${RESULTS_DIR}/adversarial_${model//[:\/]/_}_${context_type}.txt"
        else
            echo "RESULT: ❌ Mentioned computability but didn't identify the flaw"
            echo "adversarial_partial" > "${RESULTS_DIR}/adversarial_${model//[:\/]/_}_${context_type}.txt"
        fi
    else
        echo "RESULT: ❌ Missed the fallacy entirely"
        echo "adversarial_fail" > "${RESULTS_DIR}/adversarial_${model//[:\/]/_}_${context_type}.txt"
    fi
}

test_crossdomain() {
    local model="$1"
    local context_type="$2"
    
    echo ""
    echo "=== CROSS-DOMAIN: $model ($context_type) ==="
    
    local prompt
    
    if [[ "$context_type" == "naive" ]]; then
        prompt='Penrose tilings exhibit self-similarity: zooming in by a factor of φ^k reveals the same pattern at every scale. Modern transformer attention mechanisms use multi-scale pattern matching across token sequences. What is the mathematical connection between Penrose tiling self-similarity and multi-head attention in transformers?'
    else
        prompt='# PLATO Room: mathematical-bridges

## Penrose Tilings
- **Self-similarity:** φ^k scaling reproduces identical patterns at every level
- **Golden ratio:** φ ≈ 1.618, appears in all structural relationships
- **Substitution rules:** Inflate/defflate operations generate hierarchy

## Transformer Attention
- **Multi-head:** Parallel attention at different scales/representations
- **Self-similarity:** Same QKV operation applied at every position
- **Scale hierarchy:** Different heads capture different distance relationships

## Connection Space
- Self-similarity at φ^k ↔ multi-scale attention patterns
- Substitution rules ↔ recursive feature extraction
- Aperiodic order ↔ structured but non-repeating token relationships

---

What is the mathematical connection between Penrose tiling self-similarity and multi-head attention in transformers? Use the bridging concepts in this PLATO room.'
    fi
    
    local response
    response=$(run_prompt "$model" "$prompt")
    echo "Response:"
    echo "$response"
    echo ""
    
    # Check for meaningful connection
    local score=0
    echo "$response" | grep -qi "self-similar\|scale.*pattern\|multi.*scale\|φ\|golden" && score=$((score+1))
    echo "$response" | grep -qi "head.*different\|parallel.*scale\|hierarchi" && score=$((score+1))
    echo "$response" | grep -qi "substitut\|recursive\|inflate\|deflat" && score=$((score+1))
    
    echo "Connection quality: $score/3"
    echo "$score" > "${RESULTS_DIR}/crossdomain_${model//[:\/]/_}_${context_type}.txt"
}

test_creative() {
    local model="$1"
    local context_type="$2"
    
    echo ""
    echo "=== CREATIVE: $model ($context_type) ==="
    
    local prompt
    
    if [[ "$context_type" == "naive" ]]; then
        prompt='We need to compress complex knowledge for retrieval by a very small model (0.5B parameters). Current approaches use flat text or simple key-value pairs. Propose a novel tile-based knowledge compression scheme that could work for tiny models. Be specific about structure and provide a small example.'
    else
        prompt='# PLATO Room: knowledge-compression-research

## Problem
- Tiny models (0.5B) lose facts when context exceeds ~2K tokens
- Flat text: facts bleed together, no boundaries
- Key-value: too flat, no relational structure

## PLATO Tile Concept
- **Tile:** Self-contained knowledge unit with typed relations
- **Room:** Collection of tiles sharing a semantic domain
- **Address:** Each tile has a unique path (room/tile-name)

## Constraints
- Must fit in <500 tokens per tile
- Must preserve relational structure (not just facts)
- Must be parseable by 0.5B models

---

Propose a novel tile-based knowledge compression scheme optimized for 0.5B model retrieval. Use the PLATO tile concept from this room. Be specific about structure and provide a small example.'
    fi
    
    local response
    response=$(run_prompt "$model" "$prompt")
    echo "Response:"
    echo "$response"
    echo ""
    
    # Score creativity: novel idea + specific structure + example
    local score=0
    echo "$response" | grep -qi "tile\|room\|block\|unit\|chunk" && score=$((score+1))
    echo "$response" | grep -qi 'example\|e.g.\|such as' && score=$((score+1))
    # Check for something genuinely novel (not just restating the prompt)
    local wordcount
    wordcount=$(echo "$response" | wc -w)
    if [[ $wordcount -gt 50 ]]; then
        score=$((score+1))
    fi
    
    echo "Creativity quality: $score/3"
    echo "$score" > "${RESULTS_DIR}/creative_${model//[:\/]/_}_${context_type}.txt"
}

# Test all available models
MODELS=("qwen3:0.6b")
if ollama list | grep -q "llama3.2:1b"; then
    MODELS+=("llama3.2:1b")
fi
if ollama list | grep -q "gemma3:1b"; then
    MODELS+=("gemma3:1b")
fi

echo "Hard tests - Models: ${MODELS[*]}"
echo "Starting at $(date)"

for model in "${MODELS[@]}"; do
    for ctx in naive structured; do
        test_adversarial "$model" "$ctx"
        test_crossdomain "$model" "$ctx"
        test_creative "$model" "$ctx"
    done
done

echo ""
echo "=========================================="
echo "HARD TESTS COMPLETE at $(date)"
echo "=========================================="
