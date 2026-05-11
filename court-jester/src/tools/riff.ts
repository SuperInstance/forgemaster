// src/tools/riff.ts — Free-association mode (multi-turn rolling)

import { type LLMProvider, type Message } from '../providers/types.js';
import { DialogueSession } from '../dialogue/session.js';
import { SessionMemory } from '../dialogue/memory.js';

export interface RiffParams {
  topic: string;
  turns?: number;
  seedThought?: string;
  agentName?: string;
}

export interface RiffResult {
  turns: { round: number; content: string }[];
  fullTranscript: string;
  sessionPath?: string;
  tokensUsed: number;
  cost: number;
  latencyMs: number;
}

export async function riff(
  provider: LLMProvider,
  memory: SessionMemory,
  params: RiffParams
): Promise<RiffResult> {
  const maxRounds = Math.min(params.turns ?? 3, 5);

  const session = new DialogueSession(provider, memory, {
    maxRounds,
    temperature: 0.95, // Hottest temperature for free association
  });

  const initialPrompt = `Free-associate on this topic. Let your mind wander. Follow threads. Make weird connections.

Topic: ${params.topic}
${params.seedThought ? `Seed thought: ${params.seedThought}` : ''}

Rules:
- No filter. Say whatever comes to mind.
- Each response: 2-4 sentences.
- Build on your previous responses.
- If you hit something interesting, go deeper.`;

  const startTime = Date.now();

  // Use runDialogue for multi-turn
  const dialogueResult = await session.runDialogue(
    params.agentName ?? 'unknown',
    params.topic,
    'riff',
    maxRounds,
    initialPrompt
  );

  const latencyMs = Date.now() - startTime;

  const resultTurns = session.getTurnHistory().map((t) => ({
    round: t.round,
    content: t.response,
  }));

  return {
    turns: resultTurns,
    fullTranscript: dialogueResult.content,
    sessionPath: undefined, // Already saved by runDialogue
    tokensUsed: dialogueResult.session.tokenUsage,
    cost: dialogueResult.session.cost,
    latencyMs,
  };
}
