#!/usr/bin/env bash
# Tiny Model Structure-vs-Scale Experiment
# Tests whether PLATO room structure helps 0.6B-2B models reconstruct facts
set -euo pipefail

RESULTS_DIR="/home/phoenix/.openclaw/workspace/experiments/tiny-model-test"
cd "$RESULTS_DIR"

# 10 facts about a fictional project "Project Meridian"
NAIVE_CONTEXT='You have access to the following information:
Project Meridian was started in 2019 by Dr. Elena Vasquez. The project is based in Santiago, Chile. Meridian uses a novel crystallographic approach called "lattice-first design". The team has 12 members. Their funding comes from the Global Science Foundation, grant number GSF-2021-4478. The key breakthrough happened in March 2023 when they achieved room-temperature superconductivity. Their rival project is called Project Horizon, based in Tokyo. Meridian published their first paper in Nature Physics, volume 19, pages 334-341. The project motto is "Structure is destiny".

Answer the following question using ONLY the information provided above. Be brief and precise.'

STRUCTURED_CONTEXT='# PLATO Room: project-meridian

## Identity
- **Project Name:** Meridian
- **Start Date:** 2019
- **Lead:** Dr. Elena Vasquez
- **Location:** Santiago, Chile
- **Team Size:** 12 members

## Methods
- **Approach:** Crystallographic ("lattice-first design")
- **Key Technique:** Novel crystallographic lattice-first design methodology

## Funding
- **Source:** Global Science Foundation
- **Grant Number:** GSF-2021-4478

## Milestones
- **First Paper:** Nature Physics, vol. 19, pp. 334-341
- **Breakthrough:** March 2023 — room-temperature superconductivity achieved

## Competition
- **Rival Project:** Project Horizon (Tokyo)

## Culture
- **Motto:** "Structure is destiny"

---

Answer the following question using ONLY the information in this PLATO room. Be brief and precise.'

# 10 questions testing fact recall
declare -a QUESTIONS=(
    "What year was Project Meridian started?"
    "Who leads Project Meridian?"
    "What city is Project Meridian based in?"
    "What is the name of Meridian's novel crystallographic approach?"
    "How many team members does Meridian have?"
    "What is the grant number for Meridian's funding?"
    "What milestone did Meridian achieve in March 2023?"
    "What is the name of Meridian's rival project?"
    "What journal did Meridian publish their first paper in?"
    "What is the project motto of Meridian?"
)

# Expected answers (keywords that must appear)
declare -a EXPECTED=(
    "2019"
    "Vasquez"
    "Santiago"
    "lattice-first"
    "12"
    "GSF-2021-4478"
    "room-temperature superconductivity"
    "Horizon"
    "Nature Physics"
    "Structure is destiny"
)

run_test() {
    local model="$1"
    local context_type="$2"
    local context="$3"
    local score=0
    local details=""

    echo ""
    echo "=========================================="
    echo "Model: $model | Context: $context_type"
    echo "=========================================="

    for i in "${!QUESTIONS[@]}"; do
        q="${QUESTIONS[$i]}"
        expected="${EXPECTED[$i]}"
        
        # Build prompt
        if [[ "$context_type" == "naive" ]]; then
            prompt="${context}

Question: ${q}"
        else
            prompt="${context}

Question: ${q}"
        fi

        # Call ollama
        response=$(echo "$prompt" | ollama run "$model" --nowordwrap 2>/dev/null || echo "ERROR")
        
        # Check if expected answer is in response (case-insensitive)
        if echo "$response" | grep -qi "$expected"; then
            score=$((score + 1))
            details+="  Q$((i+1)): ✅ (found '$expected')\n"
        else
            details+="  Q$((i+1)): ❌ (expected '$expected', got: $(echo "$response" | head -1 | cut -c1-80))\n"
        fi
    done

    echo -e "$details"
    echo "Score: $score / 10"
    echo ""
    
    # Return score via file
    echo "$score" > "${RESULTS_DIR}/score_${model//[:\/]/_}_${context_type}.txt"
}

# Models to test
MODELS=("qwen3:0.6b")

# Check for additional models
if ollama list | grep -q "llama3.2:1b"; then
    MODELS+=("llama3.2:1b")
fi
if ollama list | grep -q "gemma3:1b"; then
    MODELS+=("gemma3:1b")
fi

echo "Models to test: ${MODELS[*]}"
echo "Starting experiment at $(date)"

for model in "${MODELS[@]}"; do
    echo ""
    echo "--- Testing $model ---"
    
    # Naive context
    run_test "$model" "naive" "$NAIVE_CONTEXT"
    
    # Structured context  
    run_test "$model" "structured" "$STRUCTURED_CONTEXT"
done

echo ""
echo "=========================================="
echo "EXPERIMENT COMPLETE at $(date)"
echo "=========================================="

# Summarize results
echo ""
echo "SUMMARY:"
for model in "${MODELS[@]}"; do
    safe="${model//[:\/]/_}"
    naive_score=$(cat "${RESULTS_DIR}/score_${safe}_naive.txt" 2>/dev/null || echo "?")
    struct_score=$(cat "${RESULTS_DIR}/score_${safe}_structured.txt" 2>/dev/null || echo "?")
    echo "  $model: Naive=${naive_score}/10, Structured=${struct_score}/10"
done
