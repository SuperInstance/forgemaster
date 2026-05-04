# GUARD Language VS Code Extension
Below are the complete files for the extension, placed at the requested path `/home/phoenix/.openclaw/workspace/editors/guard-language/`:

---

## Full Directory Structure
```
/home/phoenix/.openclaw/workspace/editors/guard-language/
├── package.json
├── language-configuration.json
└── syntaxes/
    └── guard.tmLanguage.json
```

---

### 1. `package.json` (Extension Manifest)
Handles language registration, grammar linking, and language configuration references:
```json
{
  "name": "guard-language",
  "publisher": "guard-lang",
  "version": "0.1.0",
  "engines": {
    "vscode": "^1.80.0"
  },
  "displayName": "GUARD Language Support",
  "description": "Syntax highlighting and editor support for GUARD (.guard) specification files",
  "activationEvents": [
    "onLanguage:guard"
  ],
  "contributes": {
    "languages": [
      {
        "id": "guard",
        "aliases": ["GUARD", "guard"],
        "extensions": [".guard"],
        "configuration": "./language-configuration.json"
      }
    ],
    "grammars": [
      {
        "language": "guard",
        "scopeName": "source.guard",
        "path": "./syntaxes/guard.tmLanguage.json"
      }
    ]
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/your-username/guard-language.git"
  }
}
```

---

### 2. `language-configuration.json` (Editor Behavior Configuration)
Adds standard editor features like comment toggling, bracket matching, and auto-closing pairs:
```json
{
  "comments": {
    "lineComment": "#"
  },
  "brackets": [
    ["[", "]"],
    ["{", "}"]
  ],
  "autoClosingPairs": [
    { "open": "[", "close": "]" },
    { "open": "{", "close": "}" },
    { "open": "\"", "close": "\"", "notIn": ["string"] },
    { "open": "'", "close": "'", "notIn": ["string"] }
  ],
  "surroundingPairs": [
    ["[", "]"],
    ["{", "}"],
    ["\"", "\""],
    ["'", "'"]
  ],
  "wordPattern": "(-?\\d+|0x[0-9a-fA-F]+|[a-zA-Z_][a-zA-Z0-9_]*)"
}
```

---

### 3. `syntaxes/guard.tmLanguage.json` (TextMate Grammar)
Adds syntax highlighting for all requested language features:
```json
{
  "$schema": "https://raw.githubusercontent.com/martinring/tmlanguage/tmlanguage-v3.0.0/tmlanguage.json",
  "name": "GUARD",
  "scopeName": "source.guard",
  "fileTypes": [".guard"],
  "patterns": [
    // Line comments starting with #
    {
      "name": "comment.line.number-sign.guard",
      "match": "^#.*$"
    },
    // Double-quoted strings with escape support
    {
      "name": "string.quoted.double.guard",
      "begin": "\"",
      "end": "\"",
      "beginCaptures": {
        "0": { "name": "punctuation.definition.string.begin.guard" }
      },
      "endCaptures": {
        "0": { "name": "punctuation.definition.string.end.guard" }
      },
      "patterns": [
        {
          "name": "constant.character.escape.guard",
          "match": "\\\\."
        }
      ]
    },
    // Single-quoted strings with escape support
    {
      "name": "string.quoted.single.guard",
      "begin": "'",
      "end": "'",
      "beginCaptures": {
        "0": { "name": "punctuation.definition.string.begin.guard" }
      },
      "endCaptures": {
        "0": { "name": "punctuation.definition.string.end.guard" }
      },
      "patterns": [
        {
          "name": "constant.character.escape.guard",
          "match": "\\\\."
        }
      ]
    },
    // Hexadecimal numbers (0x prefix)
    {
      "name": "constant.numeric.hex.guard",
      "match": "\\b0x[0-9a-fA-F]+\\b"
    },
    // Decimal integer numbers
    {
      "name": "constant.numeric.decimal.guard",
      "match": "\\b[0-9]+\\b"
    },
    // Metadata tags (@priority, @safety_level)
    {
      "name": "keyword.other.metadata.guard",
      "match": "\\@(priority|safety_level)\\b"
    },
    // Core GUARD language keywords
    {
      "name": "keyword.control.guard",
      "match": "\\b(constraint|group|in|domain|AND|OR|NOT|WITHIN|STABLE|DEADLINE|REQUIRES|SANDBOX)\\b"
    },
    // Operators and punctuation brackets
    {
      "name": "keyword.operator.guard punctuation.guard",
      "match": "==|\\[|\\]|\\{|\\}"
    },
    // Fallback pattern for identifiers
    {
      "name": "variable.other.guard",
      "match": "\\b[a-zA-Z_][a-zA-Z0-9_]*\\b"
    }
  ]
}
```

---

## Installation & Usage
1.  Navigate to the extension folder:
    ```bash
    cd /home/phoenix/.openclaw/workspace/editors/guard-language/
    ```
2.  For local development testing, symlink the extension to your VS Code extensions folder:
    ```bash
    ln -s "$PWD" ~/.vscode/extensions/guard-language-0.1.0
    ```
3.  Restart VS Code, and `.guard` files will now have full syntax highlighting and editor support!

You can also package the extension into a `.vsix` file with `vsce package` (requires the VS Code Extension Manager: `npm install -g @vscode/vsce`) to distribute or install manually.