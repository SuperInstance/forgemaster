// src/tools/sharpen.ts — "Iron sharpens iron" mode

import { type LLMProvider } from '../providers/types.js';
import { DialogueSession } from '../dialogue/session.js';
import { SessionMemory } from '../dialogue/memory.js';

export interface SharpenParams {
  argument: string;
  perspective?: 'logic' | 'evidence' | 'assumptions' | 'all';
  agentName?: string;
}

export interface SharpenResult {
  content: string;
  sessionPath?: string;
  tokensUsed: number;
  cost: number;
  latencyMs: number;
}

export async function sharpen(
  provider: LLMProvider,
  memory: SessionMemory,
  params: SharpenParams
): Promise<SharpenResult> {
  const perspective = params.perspective ?? 'all';

  const perspectiveInstructions: Record<string, string> = {
    logic: 'Focus on LOGICAL weaknesses. Circular reasoning, non-sequiturs, contradictions, unfounded leaps.',
    evidence: 'Focus on EVIDENCE weaknesses. Missing data, questionable sources, overgeneralization, confirmation bias.',
    assumptions: 'Focus on HIDDEN ASSUMPTIONS. What is this argument taking for granted that might not be true?',
    all: 'Attack from ALL angles — logic, evidence, and assumptions.',
  };

  const prompt = `${perspectiveInstructions[perspective]}

"IRON SHARPENS IRON" — You are the whetstone. Find the weaknesses in this argument so it can be refined.

ARGUMENT:
"""
${params.argument}
"""

Output format:
## Logical Gaps
- Gap 1: ...
- Gap 2: ...

## Brittle Assumptions
- Assumption 1: ...
- Assumption 2: ...

## Strengths (what holds up)
- Strength 1: ...
- Strength 2: ...

## Tempering Recommendation
How could this argument be strengthened?`;

  const session = new DialogueSession(provider, memory, {
    maxRounds: 1,
    temperature: 0.6, // Lower temp for analytical mode
  });

  const startTime = Date.now();
  const result = await session.singleTurn(prompt);
  const latencyMs = Date.now() - startTime;

  const sessionLog = memory.beginSession(
    params.agentName ?? 'unknown',
    `Sharpen: ${params.argument.substring(0, 60)}`,
    `sharpen-${perspective}`,
    1
  );
  memory.appendEntry(sessionLog, 'agent', prompt);
  memory.appendEntry(sessionLog, 'jester', result.content);
  sessionLog.tokenUsage = result.usage.totalTokens;
  sessionLog.cost = result.cost;
  const sessionPath = memory.finalizeSession(sessionLog);

  return {
    content: result.content,
    sessionPath,
    tokensUsed: result.usage.totalTokens,
    cost: result.cost,
    latencyMs,
  };
}
