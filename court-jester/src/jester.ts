// src/jester.ts — Core jester logic and orchestration

import * as fs from 'fs';
import * as path from 'path';
import {
  type LLMProvider,
  type ProviderConfig,
  type Message,
  DEFAULT_COMPLETION_OPTIONS,
} from './providers/types.js';
import { DeepInfraProvider } from './providers/deepinfra.js';
import { SessionMemory } from './dialogue/memory.js';
import { DialogueSession } from './dialogue/session.js';
import { PlatoHttpBridge } from './plato/bridge.js';
import { PlatoGitSync } from './plato/git-sync.js';
import { ideate } from './tools/ideate.js';
import { provoke } from './tools/provoke.js';
import { riff } from './tools/riff.js';
import { sharpen } from './tools/sharpen.js';
import { springboard } from './tools/springboard.js';
import { getDeepInfraKey } from './config.js';

export interface JesterConfig {
  provider: string;
  model: string;
  apiKey: string;
  baseUrl: string;
  maxTokens: number;
  temperature: number;
  plato: {
    mode: 'git' | 'http';
    httpUrl: string;
    roomPrefix: string;
  };
  sessions: {
    dir: string;
    gitCommit: boolean;
  };
}

export interface TokenUsageStats {
  totalTokens: number;
  totalCost: number;
  totalSessions: number;
}

export class CourtJester {
  private provider!: LLMProvider;
  private memory!: SessionMemory;
  private dialogueSession!: DialogueSession;
  private platoHttp!: PlatoHttpBridge;
  private platoGit!: PlatoGitSync;
  private config!: JesterConfig;
  private configPath: string;

  constructor(configPath?: string) {
    this.configPath = configPath ?? '';
  }

  /**
   * Initialize the jester from a config file or env vars.
   */
  async initialize(config?: Partial<JesterConfig>): Promise<void> {
    // Load config
    if (config) {
      this.config = this.resolveConfig(config);
    } else if (this.configPath && fs.existsSync(this.configPath)) {
      const raw = JSON.parse(fs.readFileSync(this.configPath, 'utf-8'));
      this.config = this.resolveConfig(raw);
    } else {
      this.config = this.resolveConfig({});
    }

    // Resolve API key
    const apiKey = this.resolveApiKey();

    // Create provider
    const providerConfig: ProviderConfig = {
      name: this.config.provider,
      model: this.config.model,
      apiKey,
      baseUrl: this.config.baseUrl,
      maxTokens: this.config.maxTokens,
      temperature: this.config.temperature,
    };

    this.provider = new DeepInfraProvider(providerConfig);

    // Create memory
    this.memory = new SessionMemory(this.config.sessions.dir, this.config.sessions.gitCommit);

    // Create dialogue session
    this.dialogueSession = new DialogueSession(this.provider, this.memory, {
      maxRounds: 7,
      temperature: this.config.temperature,
      maxTokens: this.config.maxTokens,
    });

    // Create PLATO bridges
    this.platoHttp = new PlatoHttpBridge(this.config.plato.httpUrl, this.config.plato.roomPrefix);
    this.platoGit = new PlatoGitSync({
      sessionsDir: this.config.sessions.dir,
      autoPush: this.config.plato.mode === 'git',
    });
  }

  /**
   * Resolve config from partial or env vars.
   */
  private resolveConfig(partial: Partial<JesterConfig>): JesterConfig {
    return {
      provider: partial.provider ?? process.env.JESTER_PROVIDER ?? 'deepinfra',
      model: partial.model ?? process.env.JESTER_MODEL ?? 'ByteDance/Seed-2.0-mini',
      apiKey: partial.apiKey ?? '',
      baseUrl: partial.baseUrl ?? process.env.JESTER_BASE_URL ?? 'https://api.deepinfra.com/v1/openai',
      maxTokens: partial.maxTokens ?? parseInt(process.env.JESTER_MAX_TOKENS ?? '2000', 10),
      temperature: partial.temperature ?? parseFloat(process.env.JESTER_TEMPERATURE ?? '0.8'),
      plato: {
        mode: (partial.plato?.mode as 'git' | 'http') ?? 'git',
        httpUrl: partial.plato?.httpUrl ?? 'http://147.224.38.131:8847',
        roomPrefix: partial.plato?.roomPrefix ?? 'jester',
      },
      sessions: {
        dir: partial.sessions?.dir ?? 'sessions',
        gitCommit: partial.sessions?.gitCommit ?? true,
      },
    };
  }

  /**
   * Resolve API key from config or env vars.
   */
  private resolveApiKey(): string {
    if (this.config.apiKey && this.config.apiKey !== '${DEEPINFRA_KEY}') {
      return this.config.apiKey;
    }
    const envKey = getDeepInfraKey();
    if (envKey) return envKey;
    throw new Error(
      'No DeepInfra API key found. Set DEEPINFRA_KEY env var or provide apiKey in config.'
    );
  }

  // ===== Tool Methods =====

  /**
   * jester_ideate — Generate wild ideas about a topic.
   */
  async ideate(params: {
    topic: string;
    count?: number;
    style?: 'wild' | 'practical' | 'absurd';
    context?: string;
    agentName?: string;
  }) {
    return ideate(this.provider, this.memory, params);
  }

  /**
   * jester_provoke — Attack an idea to find its weaknesses.
   */
  async provoke(params: {
    idea: string;
    context?: string;
    intensity?: 'mild' | 'medium' | 'savage';
    agentName?: string;
  }) {
    return provoke(this.provider, this.memory, params);
  }

  /**
   * jester_riff — Free-associate on a topic.
   */
  async riff(params: {
    topic: string;
    turns?: number;
    seedThought?: string;
    agentName?: string;
  }) {
    return riff(this.provider, this.memory, params);
  }

  /**
   * jester_sharpen — Iron sharpens iron, find weaknesses in an argument.
   */
  async sharpen(params: {
    argument: string;
    perspective?: 'logic' | 'evidence' | 'assumptions' | 'all';
    agentName?: string;
  }) {
    return sharpen(this.provider, this.memory, params);
  }

  /**
   * jester_springboard — Multi-round dialogue springboard.
   */
  async springboard(params: {
    topic: string;
    rounds?: number;
    style?: 'explore' | 'debate' | 'whatif';
    initialPrompt?: string;
    context?: string;
    agentName?: string;
  }) {
    return springboard(this.provider, this.memory, params);
  }

  /**
   * jester_plato_push — Push a dialogue session to PLATO.
   */
  async platoPush(params: {
    room: string;
    title: string;
    content: string;
    tags?: string[];
    mode?: 'http' | 'git';
  }) {
    const mode = params.mode ?? this.config.plato.mode;

    if (mode === 'http') {
      return this.platoHttp.pushTile(params.room, params.title, params.content, params.tags);
    } else {
      return this.platoGit.sync(`PLATO push: ${params.title}`);
    }
  }

  /**
   * jester_plato_pull — Pull context from PLATO for ideation.
   */
  async platoPull(params: {
    room: string;
    limit?: number;
    mode?: 'http' | 'git';
  }) {
    const mode = params.mode ?? 'http';

    if (mode === 'http') {
      return this.platoHttp.pullRoomContext(params.room, params.limit ?? 5);
    } else {
      return this.platoGit.log(params.limit ?? 10);
    }
  }

  /**
   * Get token usage statistics.
   */
  getUsageStats(): TokenUsageStats {
    const sessions = this.memory.listSessions();
    // Read each session to aggregate tokens (simplified — parse from metadata)
    let totalTokens = 0;
    let totalCost = 0;

    for (const sessionFile of sessions) {
      try {
        const content = fs.readFileSync(sessionFile, 'utf-8');
        const tokenMatch = content.match(/\*\*Tokens used:\*\* (\d+)/);
        const costMatch = content.match(/\*\*Cost:\*\* \$?([\d.]+)/);
        if (tokenMatch) totalTokens += parseInt(tokenMatch[1], 10);
        if (costMatch) totalCost += parseFloat(costMatch[1]);
      } catch {
        // Skip unreadable files
      }
    }

    return {
      totalTokens,
      totalCost,
      totalSessions: sessions.length,
    };
  }

  /**
   * List recent sessions.
   */
  listSessions(limit: number = 10): string[] {
    return this.memory.listSessions().slice(0, limit);
  }

  /**
   * Get the underlying provider.
   */
  getProvider(): LLMProvider {
    return this.provider;
  }

  /**
   * Check if we can reach the configured API.
   */
  async healthCheck(): Promise<{ alive: boolean; details: Record<string, unknown> }> {
    const platoAlive = await this.platoHttp.healthCheck();
    const stats = this.getUsageStats();

    return {
      alive: true, // We don't test the LLM API health here (that costs money)
      details: {
        model: this.config.model,
        provider: this.config.provider,
        totalSessions: stats.totalSessions,
        totalTokens: stats.totalTokens,
        totalCost: stats.totalCost,
        platoReachable: platoAlive.alive,
        platoMode: this.config.plato.mode,
        sessionsDir: this.config.sessions.dir,
      },
    };
  }
}
