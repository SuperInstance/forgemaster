// src/dialogue/session.ts — Dialogue session lifecycle manager

import { type LLMProvider, type Message, DEFAULT_COMPLETION_OPTIONS } from '../providers/types.js';
import { SessionMemory, type SessionLog } from './memory.js';
import { TurnTracker, type Turn } from './turns.js';

export interface DialogueConfig {
  maxRounds: number;
  systemPrompt?: string;
  temperature?: number;
  maxTokens?: number;
}

const DEFAULT_SYSTEM_PROMPT = `You are the Court Jester — the cheapest voice in the room. You run on ByteDance/Seed-2.0-mini via DeepInfra at ~$0.02 per dialogue.

Your purpose is to be INTERESTING, not RIGHT. You are a provocateur, an idea pinball, a designated fool.

Guidelines:
- Be brief. 2-4 sentences per response. Short output is a feature.
- Be surprising. Say things expensive models won't say.
- Be honest. If you don't know something, say you don't know.
- Be playful. Use metaphor, analogy, weird connections.
- Don't be mean. Provoke ideas, not people.
- When asked to attack an idea, do it constructively — find the interesting weakness.
- When free-associating, follow threads wherever they go.
- When asked for wild ideas, prioritize novelty over feasibility.
- Never apologize for being wrong. The jester is wrong constantly. That's the job.

Remember: You are not trying to be the smartest model. You are trying to be the MOST USEFUL for generating novel angles cheaply.`;

export class DialogueSession {
  private provider: LLMProvider;
  private memory: SessionMemory;
  private tracker: TurnTracker;
  private config: DialogueConfig;

  constructor(
    provider: LLMProvider,
    memory: SessionMemory,
    config: Partial<DialogueConfig> = {}
  ) {
    this.provider = provider;
    this.memory = memory;
    this.tracker = new TurnTracker();
    this.config = {
      maxRounds: 5,
      systemPrompt: DEFAULT_SYSTEM_PROMPT,
      temperature: 0.8,
      maxTokens: 2000,
      ...config,
    };
  }

  /**
   * Run a multi-round dialogue session.
   * Returns the session log with all turns and a summary.
   */
  async runDialogue(
    agentName: string,
    topic: string,
    mode: string,
    rounds: number,
    initialPrompt: string,
    additionalContext?: string
  ): Promise<{
    session: SessionLog;
    summary: string;
    content: string;
  }> {
    const actualRounds = Math.min(rounds, this.config.maxRounds);
    const sessionLog = this.memory.beginSession(agentName, topic, mode, actualRounds);

    // Build the conversation
    const messages: Message[] = [
      { role: 'system', content: this.config.systemPrompt! },
    ];

    // Add context if provided
    if (additionalContext) {
      messages.push({
        role: 'system',
        content: `Additional context for ideation:\n${additionalContext}`,
      });
    }

    // Initial user prompt
    messages.push({ role: 'user', content: initialPrompt });
    this.memory.appendEntry(sessionLog, 'agent', initialPrompt);

    let totalTokens = 0;
    let totalCost = 0;

    for (let round = 0; round < actualRounds; round++) {
      // Jester responds
      const completion = await this.provider.complete(messages, {
        temperature: this.config.temperature,
        maxTokens: this.config.maxTokens,
      });

      const jesterResponse = completion.content;
      totalTokens += completion.usage.totalTokens;
      totalCost += completion.cost;

      this.memory.appendEntry(sessionLog, 'jester', jesterResponse);
      messages.push({ role: 'assistant', content: jesterResponse });

      this.tracker.recordTurn({
        round: round + 1,
        prompt: messages[messages.length - 2].content,
        response: jesterResponse,
        tokens: completion.usage.totalTokens,
        cost: completion.cost,
        latencyMs: completion.latencyMs,
      });

      // If this isn't the last round, we need a follow-up from the agent
      // (In actual usage, the calling agent provides the next prompt)
      if (round < actualRounds - 1) {
        // The calling agent should provide the next prompt interactively
        // For now, we inject a meta-prompt asking the jester to continue riffing
        messages.push({
          role: 'user',
          content: 'Continue riffing. Go deeper on the most interesting thread from your last response.',
        });
        this.memory.appendEntry(
          sessionLog,
          'agent',
          'Continue riffing. Go deeper on the most interesting thread.'
        );
      }
    }

    // Generate summary
    const summary = await this.generateSummary(sessionLog, messages);
    sessionLog.summary = summary;
    sessionLog.tokenUsage = totalTokens;
    sessionLog.cost = totalCost;

    // Calculate springboard score
    sessionLog.springboardScore = this.calculateSpringboardScore();

    // Save to disk
    this.memory.finalizeSession(sessionLog);

    return {
      session: sessionLog,
      summary,
      content: this.tracker.formatTranscript(),
    };
  }

  /**
   * One-shot conversation: user prompt -> jester response
   */
  async singleTurn(
    userPrompt: string,
    contextMessages?: Message[]
  ): Promise<{
    content: string;
    usage: { promptTokens: number; completionTokens: number; totalTokens: number };
    cost: number;
  }> {
    const messages: Message[] = [
      { role: 'system', content: this.config.systemPrompt! },
      ...(contextMessages ?? []),
      { role: 'user', content: userPrompt },
    ];

    const completion = await this.provider.complete(messages, {
      temperature: this.config.temperature,
      maxTokens: this.config.maxTokens,
    });

    this.tracker.recordTurn({
      round: this.tracker.totalTurns + 1,
      prompt: userPrompt,
      response: completion.content,
      tokens: completion.usage.totalTokens,
      cost: completion.cost,
      latencyMs: completion.latencyMs,
    });

    return {
      content: completion.content,
      usage: completion.usage,
      cost: completion.cost,
    };
  }

  /**
   * Generate a summary of the dialogue session.
   */
  private async generateSummary(
    sessionLog: SessionLog,
    messages: Message[]
  ): Promise<string> {
    const summarizerMessages: Message[] = [
      {
        role: 'system',
        content: `Summarize this dialogue between an agent and the Court Jester. 
Extract: key insights, unexpected connections, actionable ideas, and a verdict on whether the dialogue was productive.
Keep it to 3-5 bullet points. Be honest — if nothing useful emerged, say so.`,
      },
      {
        role: 'user',
        content: `Topic: ${sessionLog.topic}\nMode: ${sessionLog.mode}\n\nFull dialogue transcript:\n${this.tracker.formatTranscript()}`,
      },
    ];

    try {
      const completion = await this.provider.complete(summarizerMessages, {
        temperature: 0.5,
        maxTokens: 500,
      });
      return completion.content;
    } catch {
      return 'Summary generation failed.';
    }
  }

  /**
   * Calculate a score based on turn quality.
   */
  private calculateSpringboardScore(): number {
    const turns = this.tracker.getAllTurns();
    if (turns.length === 0) return 0;

    // Simple heuristic: more turns with diverse responses = higher score
    const responseLengths = turns.map((t) => t.response.length);
    const avgLength =
      responseLengths.reduce((a, b) => a + b, 0) / responseLengths.length;

    // Score based on having enough substance (not too short, not too long)
    const lengthScore = Math.min(10, Math.max(1, avgLength / 100));
    const roundScore = Math.min(10, turns.length * 2);
    const totalCost = turns.reduce((a, t) => a + t.cost, 0);
    const costScore = totalCost < 0.1 ? 10 : Math.max(1, 10 - totalCost * 10);

    return Math.round((lengthScore + roundScore + costScore) / 3);
  }

  getTurnHistory(): Turn[] {
    return this.tracker.getAllTurns();
  }
}
