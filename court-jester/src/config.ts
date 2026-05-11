// src/config.ts — Configuration helpers

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

/**
 * Get the DeepInfra API key from the environment or from the credential file.
 */
export function getDeepInfraKey(): string | undefined {
  if (process.env.DEEPINFRA_KEY) {
    return process.env.DEEPINFRA_KEY;
  }

  if (process.env.DEEPINFRA_API_KEY) {
    return process.env.DEEPINFRA_API_KEY;
  }

  // Check credential file
  const credPaths = [
    path.join(os.homedir(), '.openclaw', 'workspace', '.credentials', 'deepinfra-api-key.txt'),
    path.join(os.homedir(), '.deepinfra', 'api-key.txt'),
    '.deepinfra-key',
  ];

  for (const credPath of credPaths) {
    try {
      if (fs.existsSync(credPath)) {
        return fs.readFileSync(credPath, 'utf-8').trim();
      }
    } catch {
      continue;
    }
  }

  return undefined;
}

/**
 * Load config from a JSON file, resolving env var references.
 */
export function loadConfig(configPath: string): Record<string, unknown> {
  const raw = fs.readFileSync(configPath, 'utf-8');
  // Replace ${VAR_NAME} with env vars
  const resolved = raw.replace(/\$\{(\w+)\}/g, (_, key) => {
    return process.env[key] ?? `\${${key}}`;
  });
  return JSON.parse(resolved);
}

/**
 * Get the default config path.
 */
export function getDefaultConfigPath(): string {
  const candidates = ['config.json', 'config.local.json', 'config.example.json'];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return 'config.json';
}
