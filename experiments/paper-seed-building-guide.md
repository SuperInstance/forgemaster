# BUILDING WITH COGNITIVE RESIDUE: A Practical Guide for Multi-Agent Software Engineers
You’re building a multi-agent AI system, and you’ve cut costs by using small, low-parameter models for most subtasks. But half your incorrect outputs are verbatim echoes of your input prompts, and the other half are partial, correct snippets you’ve been discarding as garbage. This guide repurposes every non-blank small model output (called cognitive residue here) into usable pipeline building blocks, with actionable routing rules, diagnostic checks, and standardized data formats you can deploy today.

## What Is Cognitive Residue?
For this guide, cognitive residue is any non-empty output from a small AI model. There are two consistent, actionable types:
1. **Echo Residue**: Output nearly identical to your input prompt
2. **Partial Residue**: Output with 1-2 accurate snippets that fails to complete the full task
Both are valuable, not noise—you’ll stop wasting compute by reusing them instead of restarting tasks from scratch.

## Routing Task Decision Tree (Copy-Pasteable Workflow)
This workflow directs every task and its residue to the right handler, no guesswork required:
```
1. TAG YOUR SUBTASK:
   a. If it’s a low-cost single-step request (lookup, simple calculation, validation, direct fact check) → send to a small model
   b. If it’s multi-step synthesis (requires combining multiple facts/steps) → send directly to a large model if you have capacity
2. RUN AUTO RESIDUE CHECK (2 lines of code):
   a. Use fuzzy string matching (e.g., FuzzyWuzzy’s `ratio()` in Python) to compare the model’s output to your original prompt. If the match score >85% → RESIDUE_TYPE = ECHO
   b. If the output has ≥1 accurate snippet but is incomplete → RESIDUE_TYPE = PARTIAL
   c. Else → USE OUTPUT DIRECTLY, no further steps
3. ROUTE:
   a. ECHO RESIDUE → send to Echo Handler workflow
   b. PARTIAL RESIDUE → send to Combiner Agent workflow
```
This cuts wasted compute by reusing residue instead of discarding it.

## Reading Wrong Answers as Diagnostics (No Theory, Just Rules)
Skip over why small models produce bad outputs—use these two rules to act fast:
- If you get echo residue: Your original prompt lacked clear guardrails against repetition. Use the echo to confirm the model grasped the task’s surface level, then add structure to push past repetition.
- If you get partial residue: The small model has the right building blocks but needs more snippets or a nudge to combine them. Don’t rerun the full task—collect more partial snippets from other small models instead.

## Standardized Data Formats & Checklist
Unstructured residue breaks multi-agent pipelines. Use these mandatory formats and checklist for every stage:

### Mandatory Data Formats
1. **Base Residue Log Format**: All small model outputs must use this machine-parsable JSON block for easy debugging and routing:
   ```json
   {
     "raw_output": "exact text the model produced",
     "task_tag": "original prompt sent to the model",
     "residue_type": "auto-labeled: echo/partial/complete"
   }
   ```
2. **Echo Stage Scaffolding Format**: Fix echo residue by sending this structured prompt to the small model for a second run:
   ```json
   {
     "original_task": "exact prompt from the first run",
     "scaffold_instruction": "Clear anti-echo direction (e.g., 'Do NOT repeat the original prompt. Instead, [specific action like fix the function]')",
     "example_non_echo": "1-sentence example of a correct, non-echo output"
   }
   ```
3. **Partial Stage Combination Format**: Send this to your combiner agent (large or small model optimized for synthesis) to merge partial snippets:
   ```json
   {
     "partial_snippets": [{"snippet": "residue text", "label": "what this snippet solves"}],
     "original_task": "full original request",
     "combine_instruction": "Clear direction to combine snippets into a complete answer"
   }
   ```

### DATA FORMAT CHECKLIST (NON-NEGOTIABLE)
✅ All residue logs use the base JSON format with no missing fields
✅ Echo remediation prompts include an explicit anti-echo rule and 1-shot example
✅ Partial combine inputs include labeled snippets to avoid confusion
✅ No more than 5 partial snippets are sent to a single combiner (small models struggle with more than this)
✅ All fields are human-readable for quick debugging
✅ Residue logs are stored in a structured database for future optimization

## Quick Real-World Build Example
Let’s walk through a bug fix workflow you can deploy today:
1. Original task: "Fix this Python function: `def add(a,b): return a*b`, then explain the change."
2. Send to a small model (e.g., Mistral 7B) → output: "`def add(a,b): return a*b`. The function should add numbers." → fuzzy match score = 88% → echo residue
3. Format the echo scaffolding prompt → resend to the small model → gets correct output: "`def add(a,b): return a + b`. This changes multiplication to addition to correctly sum inputs."
4. For partial residue: If the model outputs "`def add(a,b): return a + b`. This changes the", collect that snippet, add a label ("fixes the arithmetic operator"), and send to a combiner with another small model’s snippet: "The fix resolves incorrect addition calculations" → the combiner merges them into a full, coherent answer.

## Final Quick Win
Start by applying this workflow to one subtask type (e.g., code validation) this week. You’ll immediately cut your small model waste by ~50% (aligning with the stats you shared) and improve system accuracy without raising costs. The decision tree and checklist are ready to drop into your existing pipeline—no full rewrites required.

(Word count: ~990)
