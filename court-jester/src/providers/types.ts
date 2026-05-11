// src/providers/types.ts — LLM Provider Interface

export interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface Completion {
  content: string;
  model: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  cost: number;
  latencyMs: number;
}

export interface ProviderConfig {
  name: string;
  model: string;
  apiKey: string;
  baseUrl: string;
  maxTokens: number;
  temperature: number;
}

export interface LLMProvider {
  readonly name: string;
  readonly model: string;
  complete(messages: Message[], options?: Partial<CompletionOptions>): Promise<Completion>;
}

export interface CompletionOptions {
  maxTokens: number;
  temperature: number;
  topP: number;
}

export const DEFAULT_COMPLETION_OPTIONS: CompletionOptions = {
  maxTokens: 2000,
  temperature: 0.8,
  topP: 0.9,
};

// Cost per 1K tokens for various models (approximate USD)
export const MODEL_COST_MAP: Record<string, { input: number; output: number }> = {
  'ByteDance/Seed-2.0-mini': { input: 0.0001, output: 0.0001 },
  'ByteDance/Seed-2.0-code': { input: 0.00015, output: 0.00015 },
  'ByteDance/Seed-2.0-pro': { input: 0.0005, output: 0.0005 },
  'Qwen/Qwen3-235B-A22B-Instruct-2507': { input: 0.001, output: 0.002 },
  'NousResearch/Hermes-3-Llama-3.1-405B': { input: 0.002, output: 0.004 },
  'NousResearch/Hermes-3-Llama-3.1-70B': { input: 0.0005, output: 0.001 },
};
