// src/dialogue/memory.ts — Git-native file-based memory for sessions

import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

export interface SessionEntry {
  round: number;
  role: 'agent' | 'jester';
  content: string;
  timestamp: string;
}

export interface SessionLog {
  id: string;
  timestamp: string;
  agentName: string;
  topic: string;
  mode: string;
  rounds: number;
  entries: SessionEntry[];
  summary?: string;
  springboardScore?: number;
  tokenUsage: number;
  cost: number;
  metadata: Record<string, string>;
}

export class SessionMemory {
  private sessionsDir: string;
  private gitCommit: boolean;

  constructor(sessionsDir: string, gitCommit: boolean = true) {
    this.sessionsDir = sessionsDir;
    this.gitCommit = gitCommit;
    this.ensureDir();
  }

  private ensureDir(): void {
    if (!fs.existsSync(this.sessionsDir)) {
      fs.mkdirSync(this.sessionsDir, { recursive: true });
    }
  }

  /**
   * Create a new session ID from the current timestamp.
   */
  createSessionId(): string {
    const now = new Date();
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}-${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
  }

  /**
   * Format the current timestamp for logging.
   */
  private nowISO(): string {
    return new Date().toISOString();
  }

  /**
   * Begin a new session and return its ID.
   */
  beginSession(agentName: string, topic: string, mode: string, rounds: number): SessionLog {
    const id = this.createSessionId();
    const session: SessionLog = {
      id,
      timestamp: this.nowISO(),
      agentName,
      topic,
      mode,
      rounds,
      entries: [],
      tokenUsage: 0,
      cost: 0,
      metadata: {},
    };
    return session;
  }

  /**
   * Append an entry to the session.
   */
  appendEntry(session: SessionLog, role: 'agent' | 'jester', content: string): void {
    session.entries.push({
      round: session.entries.length + 1,
      role,
      content,
      timestamp: this.nowISO(),
    });
  }

  /**
   * Finalize and write the session file. Optionally git-commit.
   */
  finalizeSession(session: SessionLog): string {
    const filePath = path.join(this.sessionsDir, `${session.id}.md`);
    const markdown = this.renderSession(session);
    fs.writeFileSync(filePath, markdown, 'utf-8');

    if (this.gitCommit) {
      this.gitCommitFile(filePath, `Jester session: ${session.id} — ${session.topic}`);
    }

    return filePath;
  }

  /**
   * Render a session log to Markdown.
   */
  private renderSession(session: SessionLog): string {
    const lines: string[] = [];
    lines.push(`# Jester Session: ${session.id}\n`);
    lines.push('## Context');
    lines.push(`- **Agent:** ${session.agentName}`);
    lines.push(`- **Topic:** ${session.topic}`);
    lines.push(`- **Mode:** ${session.mode} (${session.rounds} rounds)`);
    lines.push(`- **Started:** ${session.timestamp}`);
    if (session.metadata && Object.keys(session.metadata).length > 0) {
      for (const [key, val] of Object.entries(session.metadata)) {
        lines.push(`- **${key}:** ${val}`);
      }
    }
    lines.push('');

    for (const entry of session.entries) {
      lines.push(`## Round ${entry.round}`);
      const emoji = entry.role === 'agent' ? '🤖' : '🃏';
      lines.push(`**${emoji} ${entry.role === 'agent' ? 'Agent' : 'Jester'}:**`);
      lines.push('');
      lines.push(entry.content);
      lines.push('');
    }

    if (session.summary) {
      lines.push('## Summary');
      lines.push(session.summary);
      lines.push('');
    }

    lines.push('---');
    lines.push('_Session metadata:_');
    lines.push(`- **Total rounds:** ${session.entries.length}`);
    lines.push(`- **Tokens used:** ${session.tokenUsage}`);
    lines.push(`- **Cost:** \$${session.cost.toFixed(4)}`);
    if (session.springboardScore !== undefined) {
      lines.push(`- **Springboard score:** ${session.springboardScore}/10`);
    }

    return lines.join('\n');
  }

  /**
   * List all session files, newest first.
   */
  listSessions(): string[] {
    if (!fs.existsSync(this.sessionsDir)) return [];
    return fs
      .readdirSync(this.sessionsDir)
      .filter((f) => f.endsWith('.md'))
      .sort()
      .reverse()
      .map((f) => path.join(this.sessionsDir, f));
  }

  /**
   * Read a session file and parse it (simple line-based summary).
   */
  readSessionSummary(filePath: string): string {
    if (!fs.existsSync(filePath)) {
      return `Session file not found: ${filePath}`;
    }
    const content = fs.readFileSync(filePath, 'utf-8');
    // Return first ~20 lines as summary
    return content.split('\n').slice(0, 20).join('\n');
  }

  /**
   * Git-commit the session file.
   */
  private gitCommitFile(filePath: string, message: string): void {
    try {
      // Check if we're in a git repo
      execSync('git rev-parse --git-dir', {
        cwd: this.sessionsDir,
        stdio: 'ignore',
      });
      execSync(`git add "${filePath}"`, { cwd: this.sessionsDir, stdio: 'ignore' });
      execSync(`git commit -m "${message}"`, { cwd: this.sessionsDir, stdio: 'ignore' });
    } catch {
      // Not a git repo or git not available — that's fine
    }
  }
}
