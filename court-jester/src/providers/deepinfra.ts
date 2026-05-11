// src/providers/deepinfra.ts — DeepInfra API client (Seed-2.0-mini and friends)

import {
  type LLMProvider,
  type ProviderConfig,
  type Message,
  type Completion,
  type CompletionOptions,
  DEFAULT_COMPLETION_OPTIONS,
  MODEL_COST_MAP,
} from './types.js';

export class DeepInfraProvider implements LLMProvider {
  readonly name: string;
  readonly model: string;
  private config: ProviderConfig;

  constructor(config: ProviderConfig) {
    this.config = config;
    this.name = config.name;
    this.model = config.model;
  }

  async complete(
    messages: Message[],
    options?: Partial<CompletionOptions>
  ): Promise<Completion> {
    const opts = { ...DEFAULT_COMPLETION_OPTIONS, ...options };
    const startTime = Date.now();

    const body = {
      model: this.model,
      messages,
      max_tokens: opts.maxTokens,
      temperature: opts.temperature,
      top_p: opts.topP,
    };

    const response = await fetch(`${this.config.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorBody = await response.text().catch(() => 'unknown');
      throw new Error(
        `DeepInfra API error: ${response.status} ${response.statusText} — ${errorBody}`
      );
    }

    const data = (await response.json()) as {
      choices: { message: { content: string } }[];
      usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
      model: string;
    };

    const latencyMs = Date.now() - startTime;
    const promptTokens = data.usage.prompt_tokens;
    const completionTokens = data.usage.completion_tokens;
    const totalTokens = data.usage.total_tokens;

    // Calculate cost based on model pricing, fall back to default
    const pricing = MODEL_COST_MAP[this.model] || { input: 0.0001, output: 0.0001 };
    const cost =
      (promptTokens / 1000) * pricing.input +
      (completionTokens / 1000) * pricing.output;

    return {
      content: data.choices[0]?.message?.content ?? '',
      model: data.model ?? this.model,
      usage: {
        promptTokens,
        completionTokens,
        totalTokens,
      },
      cost,
      latencyMs,
    };
  }
}
