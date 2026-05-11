// src/tools/springboard.ts — Multi-round dialogue springboard

import { type LLMProvider } from '../providers/types.js';
import { DialogueSession } from '../dialogue/session.js';
import { SessionMemory } from '../dialogue/memory.js';

export interface SpringboardParams {
  topic: string;
  rounds?: number;
  style?: 'explore' | 'debate' | 'whatif';
  initialPrompt?: string;
  context?: string;
  agentName?: string;
}

export interface SpringboardResult {
  summary: string;
  fullTranscript: string;
  sessionPath?: string;
  springboardScore: number;
  tokensUsed: number;
  cost: number;
  latencyMs: number;
  roundCount: number;
}

export async function springboard(
  provider: LLMProvider,
  memory: SessionMemory,
  params: SpringboardParams
): Promise<SpringboardResult> {
  const rounds = Math.min(params.rounds ?? 5, 7);
  const style = params.style ?? 'explore';

  const stylePrompts: Record<string, string> = {
    explore:
      'I want to explore this topic from multiple angles. Each round, take a DIFFERENT perspective. Don\'t repeat yourself. If the topic has N dimensions, try to touch all of them.',
    debate:
      'I want to DEBATE this topic. You take the contrarian position to whatever I say. If I say left, you say right. Challenge everything. Find the weak points in my reasoning and push on them.',
    whatif:
      'I want to play "WHAT IF?" with this topic. Each round, change one fundamental assumption. "What if gravity worked backwards?" "What if time was a resource?" Keep twisting.',
  };

  const initialPrompt =
    params.initialPrompt ??
    `${stylePrompts[style]}

Topic to explore: ${params.topic}

${params.context ? `Context for grounding: ${params.context}` : ''}

Round 1: Start with your most interesting angle.`;

  const session = new DialogueSession(provider, memory, {
    maxRounds: rounds,
    temperature: 0.85,
  });

  const startTime = Date.now();
  const result = await session.runDialogue(
    params.agentName ?? 'unknown',
    params.topic,
    `springboard-${style}`,
    rounds,
    initialPrompt
  );
  const latencyMs = Date.now() - startTime;

  return {
    summary: result.summary,
    fullTranscript: result.content,
    sessionPath: undefined, // Saved by runDialogue
    springboardScore: result.session.springboardScore ?? 5,
    tokensUsed: result.session.tokenUsage,
    cost: result.session.cost,
    latencyMs,
    roundCount: result.session.entries.length,
  };
}
