// src/plato/git-sync.ts — Git-based PLATO bridge (offline-first)

import * as fs from 'fs';
import * as path from 'path';
import { execSync, type ExecSyncOptions } from 'child_process';

export interface GitSyncConfig {
  sessionsDir: string;
  remoteUrl?: string;
  remoteName?: string;
  branch?: string;
  autoPush: boolean;
}

export class PlatoGitSync {
  private config: GitSyncConfig;

  constructor(config: Partial<GitSyncConfig> = {}) {
    this.config = {
      sessionsDir: config.sessionsDir ?? 'sessions',
      remoteUrl: config.remoteUrl,
      remoteName: config.remoteName ?? 'plato',
      branch: config.branch ?? 'main',
      autoPush: config.autoPush ?? false,
    };
  }

  /**
   * Initialize the sessions directory as a git repo.
   */
  initRepo(): { success: boolean; error?: string } {
    const gitDir = path.join(this.config.sessionsDir, '.git');
    if (fs.existsSync(gitDir)) {
      return { success: true }; // Already a repo
    }

    try {
      execSync('git init', { cwd: this.config.sessionsDir, stdio: 'ignore' });
      execSync('git checkout -b ' + this.config.branch, {
        cwd: this.config.sessionsDir,
        stdio: 'ignore',
      });

      // Set remote if provided
      if (this.config.remoteUrl) {
        execSync(
          `git remote add ${this.config.remoteName} ${this.config.remoteUrl}`,
          { cwd: this.config.sessionsDir, stdio: 'ignore' }
        );
      }

      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { success: false, error: `Git init failed: ${message}` };
    }
  }

  /**
   * Commit all session files and optionally push.
   */
  sync(message: string = 'Jester session sync'): { success: boolean; error?: string } {
    try {
      // Ensure we're in a git repo
      this.initRepo();

      execSync(`git add -A`, { cwd: this.config.sessionsDir, stdio: 'ignore' });

      // Check if there's anything to commit
      const status = execSync('git status --porcelain', {
        cwd: this.config.sessionsDir,
        encoding: 'utf-8',
      });
      if (!status.trim()) {
        return { success: true }; // Nothing to commit
      }

      execSync(`git commit -m "${message}"`, {
        cwd: this.config.sessionsDir,
        stdio: 'ignore',
      });

      if (this.config.autoPush && this.config.remoteUrl) {
        return this.push();
      }

      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { success: false, error: `Git sync failed: ${message}` };
    }
  }

  /**
   * Push to the PLATO remote.
   */
  push(): { success: boolean; error?: string } {
    if (!this.config.remoteUrl) {
      return { success: false, error: 'No remote URL configured for PLATO sync' };
    }

    try {
      execSync(
        `git push ${this.config.remoteName} ${this.config.branch}`,
        { cwd: this.config.sessionsDir, stdio: 'ignore' }
      );
      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { success: false, error: `Git push failed: ${message}` };
    }
  }

  /**
   * Pull from the PLATO remote.
   */
  pull(): { success: boolean; error?: string } {
    if (!this.config.remoteUrl) {
      return { success: false, error: 'No remote URL configured for PLATO sync' };
    }

    try {
      execSync(
        `git pull ${this.config.remoteName} ${this.config.branch}`,
        { cwd: this.config.sessionsDir, stdio: 'ignore' }
      );
      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { success: false, error: `Git pull failed: ${message}` };
    }
  }

  /**
   * Get the git log for the sessions repo.
   */
  log(limit: number = 10): { success: boolean; entries?: string[]; error?: string } {
    try {
      const output = execSync(
        `git log --oneline -${limit}`,
        { cwd: this.config.sessionsDir, encoding: 'utf-8' }
      );
      const entries = output.trim().split('\n').filter(Boolean);
      return { success: true, entries };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { success: false, error: `Git log failed: ${message}` };
    }
  }

  /**
   * Sync using the config file.
   */
  setRemote(url: string, name: string = 'plato'): { success: boolean; error?: string } {
    this.config.remoteUrl = url;
    this.config.remoteName = name;

    try {
      // Remove existing remote if present, then add
      try {
        execSync(`git remote rm ${name}`, {
          cwd: this.config.sessionsDir,
          stdio: 'ignore',
        });
      } catch {
        // No existing remote
      }

      execSync(`git remote add ${name} ${url}`, {
        cwd: this.config.sessionsDir,
        stdio: 'ignore',
      });
      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { success: false, error: `Set remote failed: ${message}` };
    }
  }
}
