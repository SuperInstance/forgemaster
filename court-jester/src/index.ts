#!/usr/bin/env node

// src/index.ts — MCP Server Entry Point

import * as fs from 'fs';
import * as path from 'path';
import { CourtJester, type JesterConfig } from './jester.js';
import { getDefaultConfigPath, loadConfig } from './config.js';

// ===== MCP Protocol Helpers =====

interface JsonRpcRequest {
  jsonrpc: '2.0';
  id: string | number;
  method: string;
  params?: Record<string, unknown>;
}

interface JsonRpcResponse {
  jsonrpc: '2.0';
  id: string | number;
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

interface McpInitializeParams {
  protocolVersion: string;
  capabilities?: Record<string, unknown>;
  clientInfo?: { name: string; version: string };
}

interface McpTool {
  name: string;
  description: string;
  inputSchema: {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
  };
}

// ===== MCP Server =====

class CourtJesterMcpServer {
  private jester: CourtJester;
  private initialized = false;
  private clientInfo: { name: string; version: string } | null = null;

  constructor() {
    this.jester = new CourtJester();
  }

  /**
   * Tool definitions exposed to MCP clients.
   */
  private getTools(): McpTool[] {
    return [
      {
        name: 'jester_ideate',
        description:
          'Generate wild/practical/absurd ideas about a topic. The jester produces rapid-fire ideas at ~$0.02/session. Use when you need novel angles fast.',
        inputSchema: {
          type: 'object',
          properties: {
            topic: {
              type: 'string',
              description: 'The topic to generate ideas about',
            },
            count: {
              type: 'number',
              description: 'Number of ideas to generate (default: 5)',
              default: 5,
            },
            style: {
              type: 'string',
              description: 'Style of ideation: wild, practical, or absurd (default: wild)',
              enum: ['wild', 'practical', 'absurd'],
              default: 'wild',
            },
            context: {
              type: 'string',
              description: 'Optional context to ground the ideation',
            },
          },
          required: ['topic'],
        },
      },
      {
        name: 'jester_provoke',
        description:
          'Attack an idea to find its weaknesses. The jester plays contrarian to stress-test your thinking. Choose intensity from mild (constructive) to savage (brutal).',
        inputSchema: {
          type: 'object',
          properties: {
            idea: {
              type: 'string',
              description: 'The idea to attack and stress-test',
            },
            context: {
              type: 'string',
              description: 'Optional context about the idea',
            },
            intensity: {
              type: 'string',
              description: 'Attack intensity: mild, medium, or savage (default: medium)',
              enum: ['mild', 'medium', 'savage'],
              default: 'medium',
            },
          },
          required: ['idea'],
        },
      },
      {
        name: 'jester_riff',
        description:
          'Free-associate on a topic across multiple turns. The jester lets its mind wander at max temperature. Best for creative block or exploring a space without preconceptions.',
        inputSchema: {
          type: 'object',
          properties: {
            topic: {
              type: 'string',
              description: 'Topic to free-associate on',
            },
            turns: {
              type: 'number',
              description: 'Number of riff turns (default: 3, max: 5)',
              default: 3,
            },
            seedThought: {
              type: 'string',
              description: 'Optional seed thought to start from',
            },
          },
          required: ['topic'],
        },
      },
      {
        name: 'jester_sharpen',
        description:
          '"Iron sharpens iron" — have the jester find logical gaps, brittle assumptions, and hidden weaknesses in an argument. Returns both weaknesses AND strengths.',
        inputSchema: {
          type: 'object',
          properties: {
            argument: {
              type: 'string',
              description: 'The argument or position to sharpen',
            },
            perspective: {
              type: 'string',
              description: 'Focus on logic, evidence, assumptions, or all (default: all)',
              enum: ['logic', 'evidence', 'assumptions', 'all'],
              default: 'all',
            },
          },
          required: ['argument'],
        },
      },
      {
        name: 'jester_springboard',
        description:
          'Run N rounds of multi-turn dialogue about a topic, then summarize what emerged. The jester can explore (try different angles), debate (play contrarian), or what-if (twist assumptions). Returns a summary + full transcript.',
        inputSchema: {
          type: 'object',
          properties: {
            topic: {
              type: 'string',
              description: 'Topic for the springboard session',
            },
            rounds: {
              type: 'number',
              description: 'Number of dialogue rounds (default: 5, max: 7)',
              default: 5,
            },
            style: {
              type: 'string',
              description: 'Dialogue style: explore, debate, or whatif (default: explore)',
              enum: ['explore', 'debate', 'whatif'],
              default: 'explore',
            },
            initialPrompt: {
              type: 'string',
              description: 'Optional custom initial prompt for the jester',
            },
            context: {
              type: 'string',
              description: 'Optional context to ground the dialogue',
            },
          },
          required: ['topic'],
        },
      },
      {
        name: 'jester_plato_push',
        description:
          'Push a dialogue or ideation session to a PLATO room. Uses HTTP (REST) or git (filesystem). Defaults to HTTP.',
        inputSchema: {
          type: 'object',
          properties: {
            room: {
              type: 'string',
              description: 'PLATO room name (e.g., "ideations/temporal-perception")',
            },
            title: {
              type: 'string',
              description: 'Title for the PLATO tile or commit',
            },
            content: {
              type: 'string',
              description: 'Content to push (session summary or full transcript)',
            },
            tags: {
              type: 'array',
              items: { type: 'string' },
              description: 'Optional tags for the PLATO tile',
            },
            mode: {
              type: 'string',
              description: 'Push mode: http or git (default: http)',
              enum: ['http', 'git'],
              default: 'http',
            },
          },
          required: ['room', 'title', 'content'],
        },
      },
      {
        name: 'jester_plato_pull',
        description:
          'Pull context from a PLATO room to prime the jester for ideation. Returns recent tiles/commits that can be used as grounding context.',
        inputSchema: {
          type: 'object',
          properties: {
            room: {
              type: 'string',
              description: 'PLATO room name to pull from',
            },
            limit: {
              type: 'number',
              description: 'Number of tiles/commits to pull (default: 5)',
              default: 5,
            },
            mode: {
              type: 'string',
              description: 'Pull mode: http or git (default: http)',
              enum: ['http', 'git'],
              default: 'http',
            },
          },
          required: ['room'],
        },
      },
    ];
  }

  /**
   * Handle an incoming JSON-RPC request.
   */
  async handleRequest(request: JsonRpcRequest): Promise<JsonRpcResponse> {
    const base: JsonRpcResponse = {
      jsonrpc: '2.0',
      id: request.id,
    };

    try {
      switch (request.method) {
        // ===== MCP Lifecycle =====

        case 'initialize': {
          const params = request.params as McpInitializeParams | undefined;
          this.clientInfo = params?.clientInfo ?? null;
          await this.jester.initialize();
          this.initialized = true;

          return {
            ...base,
            result: {
              protocolVersion: params?.protocolVersion ?? '2024-11-05',
              capabilities: {
                tools: {}, // Signal we support tools
              },
              serverInfo: {
                name: 'court-jester',
                version: '0.1.0',
              },
            },
          };
        }

        case 'notifications/initialized': {
          return { ...base, result: null };
        }

        // ===== Tools =====

        case 'tools/list': {
          if (!this.initialized) {
            return {
              ...base,
              error: { code: -32000, message: 'Server not initialized' },
            };
          }
          return {
            ...base,
            result: {
              tools: this.getTools(),
            },
          };
        }

        case 'tools/call': {
          if (!this.initialized) {
            return {
              ...base,
              error: { code: -32000, message: 'Server not initialized' },
            };
          }

          const toolParams = request.params as {
            name: string;
            arguments?: Record<string, unknown>;
          };

          return await this.handleToolCall(toolParams.name, toolParams.arguments ?? {}, base);
        }

        // ===== Ping / Health =====

        case 'ping': {
          return { ...base, result: 'pong' };
        }

        default: {
          return {
            ...base,
            error: {
              code: -32601,
              message: `Method not found: ${request.method}`,
            },
          };
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        ...base,
        error: {
          code: -32603,
          message: `Internal error: ${message}`,
        },
      };
    }
  }

  /**
   * Dispatch a tool call to the appropriate handler.
   */
  private async handleToolCall(
    toolName: string,
    args: Record<string, unknown>,
    base: JsonRpcResponse
  ): Promise<JsonRpcResponse> {
    try {
      switch (toolName) {
        case 'jester_ideate': {
          const result = await this.jester.ideate({
            topic: args.topic as string,
            count: (args.count as number) ?? 5,
            style: (args.style as 'wild' | 'practical' | 'absurd') ?? 'wild',
            context: args.context as string | undefined,
          });
          return {
            ...base,
            result: {
              content: [
                {
                  type: 'text',
                  text: result.content,
                },
                {
                  type: 'text',
                  text: `---\nToken cost: ${result.tokensUsed} ($${result.cost.toFixed(4)}) | Latency: ${result.latencyMs}ms`,
                },
              ],
            },
          };
        }

        case 'jester_provoke': {
          const result = await this.jester.provoke({
            idea: args.idea as string,
            context: args.context as string | undefined,
            intensity: (args.intensity as 'mild' | 'medium' | 'savage') ?? 'medium',
          });
          return {
            ...base,
            result: {
              content: [
                {
                  type: 'text',
                  text: result.content,
                },
                {
                  type: 'text',
                  text: `---\nToken cost: ${result.tokensUsed} ($${result.cost.toFixed(4)}) | Latency: ${result.latencyMs}ms`,
                },
              ],
            },
          };
        }

        case 'jester_riff': {
          const result = await this.jester.riff({
            topic: args.topic as string,
            turns: (args.turns as number) ?? 3,
            seedThought: args.seedThought as string | undefined,
          });
          return {
            ...base,
            result: {
              content: [
                ...result.turns.map((t, i) => ({
                  type: 'text' as const,
                  text: `**Riff Round ${i + 1}:**\n${t.content}`,
                })),
                {
                  type: 'text',
                  text: `---\nRounds: ${result.turns.length} | Tokens: ${result.tokensUsed} ($${result.cost.toFixed(4)}) | Latency: ${result.latencyMs}ms`,
                },
              ],
            },
          };
        }

        case 'jester_sharpen': {
          const result = await this.jester.sharpen({
            argument: args.argument as string,
            perspective: (args.perspective as 'logic' | 'evidence' | 'assumptions' | 'all') ?? 'all',
          });
          return {
            ...base,
            result: {
              content: [
                {
                  type: 'text',
                  text: result.content,
                },
                {
                  type: 'text',
                  text: `---\nToken cost: ${result.tokensUsed} ($${result.cost.toFixed(4)}) | Latency: ${result.latencyMs}ms`,
                },
              ],
            },
          };
        }

        case 'jester_springboard': {
          const result = await this.jester.springboard({
            topic: args.topic as string,
            rounds: (args.rounds as number) ?? 5,
            style: (args.style as 'explore' | 'debate' | 'whatif') ?? 'explore',
            initialPrompt: args.initialPrompt as string | undefined,
            context: args.context as string | undefined,
          });
          return {
            ...base,
            result: {
              content: [
                {
                  type: 'text',
                  text: `## Springboard Summary (Score: ${result.springboardScore}/10)\n\n${result.summary}`,
                },
                {
                  type: 'text',
                  text: `## Full Transcript\n\n${result.fullTranscript}`,
                },
                {
                  type: 'text',
                  text: `---\nRounds: ${result.roundCount} | Tokens: ${result.tokensUsed} ($${result.cost.toFixed(4)}) | Latency: ${result.latencyMs}ms | Score: ${result.springboardScore}/10`,
                },
              ],
            },
          };
        }

        case 'jester_plato_push': {
          const result = await this.jester.platoPush({
            room: args.room as string,
            title: args.title as string,
            content: args.content as string,
            tags: args.tags as string[] | undefined,
            mode: (args.mode as 'http' | 'git') ?? 'http',
          });
          return {
            ...base,
            result: {
              content: [
                {
                  type: 'text',
                  text: result.success
                    ? `✅ Successfully pushed to PLATO room "${args.room}"`
                    : `❌ Failed: ${result.error ?? 'Unknown error'}`,
                },
              ],
            },
          };
        }

        case 'jester_plato_pull': {
          const result = await this.jester.platoPull({
            room: args.room as string,
            limit: (args.limit as number) ?? 5,
            mode: (args.mode as 'http' | 'git') ?? 'http',
          });
          return {
            ...base,
            result: {
              content: [
                {
                  type: 'text',
                  text: result.success
                    ? `Pulled ${(result as { tiles?: unknown[] }).tiles?.length ?? (result as { entries?: string[] }).entries?.length ?? 0} items from PLATO room "${args.room}"`
                    : `❌ Failed: ${(result as { error?: string }).error ?? 'Unknown error'}`,
                },
              ],
            },
          };
        }

        default:
          return {
            ...base,
            error: {
              code: -32602,
              message: `Unknown tool: ${toolName}`,
            },
          };
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        ...base,
        error: {
          code: -32603,
          message: `Tool execution error: ${message}`,
        },
      };
    }
  }
}

// ===== MCP Transport: stdio =====

async function main() {
  const server = new CourtJesterMcpServer();

  process.stdin.setEncoding('utf-8');
  let buffer = '';

  // Log status to stderr (MCP uses stdin/stdout for JSON-RPC)
  process.stderr.write('Court Jester MCP server starting...\n');

  // Handle incoming JSON-RPC messages line by line
  process.stdin.on('data', async (chunk: string) => {
    buffer += chunk;

    // Process complete lines
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? ''; // Keep incomplete line in buffer

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      try {
        const request: JsonRpcRequest = JSON.parse(trimmed);
        const response = await server.handleRequest(request);

        if (response) {
          process.stdout.write(JSON.stringify(response) + '\n');
        }
      } catch (parseErr) {
        const message = parseErr instanceof Error ? parseErr.message : String(parseErr);
        process.stderr.write(`Failed to parse request: ${message}\n`);
        process.stdout.write(
          JSON.stringify({
            jsonrpc: '2.0',
            id: null,
            error: { code: -32700, message: `Parse error: ${message}` },
          }) + '\n'
        );
      }
    }
  });

  process.stdin.on('end', () => {
    process.stderr.write('Court Jester MCP server shutting down.\n');
    process.exit(0);
  });

  process.on('SIGINT', () => {
    process.stderr.write('Received SIGINT, shutting down.\n');
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    process.stderr.write('Received SIGTERM, shutting down.\n');
    process.exit(0);
  });

  process.stderr.write('Court Jester MCP server ready on stdin/stdout.\n');
}

main().catch((err) => {
  process.stderr.write(`Fatal error: ${err}\n`);
  process.exit(1);
});
