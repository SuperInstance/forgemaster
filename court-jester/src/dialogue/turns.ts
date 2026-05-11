// src/dialogue/turns.ts — Turn tracking for dialogue sessions

export interface Turn {
  round: number;
  prompt: string;
  response: string;
  tokens: number;
  cost: number;
  latencyMs: number;
  timestamp: string;
}

export class TurnTracker {
  private turns: Turn[] = [];

  recordTurn(turn: Omit<Turn, 'timestamp'>): void {
    this.turns.push({
      ...turn,
      timestamp: new Date().toISOString(),
    });
  }

  getAllTurns(): Turn[] {
    return [...this.turns];
  }

  get totalTurns(): number {
    return this.turns.length;
  }

  get totalTokens(): number {
    return this.turns.reduce((sum, t) => sum + t.tokens, 0);
  }

  get totalCost(): number {
    return this.turns.reduce((sum, t) => sum + t.cost, 0);
  }

  get totalLatency(): number {
    return this.turns.reduce((sum, t) => sum + t.latencyMs, 0);
  }

  formatTranscript(): string {
    return this.turns
      .map(
        (t) =>
          `[Round ${t.round}]\nAgent: ${t.prompt}\nJester: ${t.response}\n`
      )
      .join('\n');
  }

  reset(): void {
    this.turns = [];
  }
}
