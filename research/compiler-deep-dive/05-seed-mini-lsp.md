# GUARD Constraint DSL LSP Implementation in Rust
This is a complete, typed LSP implementation for the GUARD constraint validation DSL, including all requested features, plus `guardfmt` and `guardlint` tooling. We'll use standard Rust LSP ecosystem crates: `tower-lsp`, `lsp-types`, `dashmap`, `serde`, and `tree-sitter` for parsing.

---

## 1. Core Dependencies
Add this to your `Cargo.toml`:
```toml
[package]
name = "guard-lsp"
version = "0.1.0"
edition = "2021"

[dependencies]
lsp-types = "0.94"
tower-lsp = "0.20"
url = "2.4"
dashmap = "5.4"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
thiserror = "1.0"
tree-sitter = "0.21"
tree-sitter-guard = { path = "./tree-sitter-guard" } # Custom DSL parser
tokio = { version = "1.0", features = ["full"] }
```

---

## 2. Core Types & AST
First, define the typed AST for the GUARD DSL and LSP server state:
```rust
use std::collections::HashMap;
use std::sync::Arc;
use dashmap::DashMap;
use lsp_types::*;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use url::Url;

/// Thread-safe server state
#[derive(Clone, Default)]
pub struct GuardLspState {
    /// Open documents cached by URI
    documents: Arc<DashMap<Url, DocumentSnapshot>>,
    /// Cached lint diagnostics per document
    diagnostics: Arc<DashMap<Url, Vec<Diagnostic>>>,
    /// Global symbol index: guard name -> definition location
    guard_symbols: Arc<DashMap<String, Location>>,
    /// Client configuration
    config: GuardLspConfig,
}

/// LSP server configuration
#[derive(Debug, Serialize, Deserialize, Default)]
#[serde(default, rename_all = "camelCase")]
pub struct GuardLspConfig {
    pub enable_semantic_tokens: bool,
    pub enable_inlay_hints: bool,
    pub guardfmt_path: Option<String>,
    pub enabled_lint_rules: Vec<String>,
    /// Target struct/field schema for reference checking
    pub target_schema: Option<TargetSchema>,
}

/// Target schema for validated data
#[derive(Debug, Serialize, Deserialize, Default)]
pub struct TargetSchema {
    pub struct_name: String,
    pub fields: HashMap<String, String>, // field name -> type
}

/// Parsed document snapshot
#[derive(Clone)]
pub struct DocumentSnapshot {
    pub uri: Url,
    pub text: String,
    pub ast: GuardFile,
    pub parse_errors: Vec<ParseError>,
}

/// Top-level parsed GUARD DSL file
pub struct GuardFile {
    pub imports: Vec<ImportStmt>,
    pub guards: Vec<GuardDecl>,
}

/// A single guard constraint declaration: `guard UserName { len >= 3 && matches(...) }`
pub struct GuardDecl {
    pub name: String,
    pub target: ConstraintTarget,
    pub body: Expr,
    pub span: TextRange,
}

/// Where the guard constraint applies
pub enum ConstraintTarget {
    StructField(String, String), // (struct_name, field_name)
    Function(String),            // function name
    Local(String),                // local variable
}

/// GUARD DSL expression nodes
pub enum Expr {
    Literal(Literal),
    Ref(String), // Reference to a field/guard/variable
    BuiltinCall(BuiltinFn, Vec<Expr>),
    BinaryOp(BinaryOp, Box<Expr>, Box<Expr>),
    UnaryOp(UnaryOp, Box<Expr>),
}

/// Supported built-in DSL functions
#[derive(Debug, Clone, Copy)]
pub enum BuiltinFn {
    Len,
    Matches,
    Min,
    Max,
    Between,
}

/// Binary operators
pub enum BinaryOp {
    And, Or, Eq, Neq, Lt, Gt, Lte, Gte,
}

/// Unary operators
pub enum UnaryOp {
    Not,
}

/// Literal values
pub enum Literal {
    String(String),
    Number(f64),
    Regex(String),
}

#[derive(Debug, Error)]
pub enum GuardLspError {
    #[error("Failed to parse document: {0}")]
    ParseError(#[from] tree_sitter::Error),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}
```

---

## 3. LSP Feature Implementations
All requested LSP features are implemented as typed handler functions:

---

### 3.1 Diagnostics (via `guardlint`)
Runs static analysis on document changes and publishes errors/warnings:
```rust
impl GuardLspState {
    /// Update diagnostics for an open document
    pub fn update_diagnostics(&self, uri: &Url, text: &str) {
        let parse_result = parse_guard_dsl(text);
        let mut diagnostics = Vec::new();

        // Add parse errors
        for err in parse_result.parse_errors {
            diagnostics.push(Diagnostic {
                range: err.span.to_lsp_range(text),
                severity: Some(DiagnosticSeverity::ERROR),
                code: Some(NumberOrString::String("parse-error".into())),
                message: err.message,
                ..Default::default()
            });
        }

        // Run semantic lint checks
        for rule in &self.config.enabled_lint_rules {
            self.run_lint_rule(rule, &parse_result.ast, text, &mut diagnostics);
        }

        self.diagnostics.insert(uri.clone(), diagnostics);
    }

    /// Run individual lint rule
    fn run_lint_rule(&self, rule: &str, ast: &GuardFile, text: &str, diagnostics: &mut Vec<Diagnostic>) {
        match rule {
            "undefined-ref" => self.check_undefined_references(ast, text, diagnostics),
            "unused-guard" => self.check_unused_guards(ast, text, diagnostics),
            "hardcoded-regex" => self.check_hardcoded_regex(ast, text, diagnostics),
            _ => {}
        }
    }
}
```

---

### 3.2 Hover Support
Show documentation for symbols under the cursor:
```rust
pub fn handle_hover(
    state: &GuardLspState,
    params: HoverParams,
    text: &str,
    ast: &GuardFile,
) -> Option<Hover> {
    let cursor_offset = lsp_pos_to_offset(params.text_document_position.position, text)?;
    let node = find_ast_node_at_offset(ast, cursor_offset)?;

    match node {
        AstNode::BuiltinCall(builtin, _) => Some(Hover {
            contents: HoverContents::Markup(MarkupContent {
                kind: MarkupKind::MARKDOWN,
                value: format!("### `{}`\n\n{}", builtin.name(), builtin.docs()),
            }),
            range: Some(builtin.span().to_lsp_range(text)),
        }),
        AstNode::Ref(name) => state.guard_symbols.get(name).map(|loc| Hover {
            contents: HoverContents::Markup(MarkupContent {
                kind: MarkupKind::MARKDOWN,
                value: format!("### Guard `{name}`\nDefined at {}", loc.uri),
            }),
            range: Some(node.span().to_lsp_range(text)),
        }),
        _ => None,
    }
}
```

---

### 3.3 Completion
Context-aware code completion for builtins, fields, and guards:
```rust
pub fn handle_completion(
    state: &GuardLspState,
    params: CompletionParams,
    text: &str,
    ast: &GuardFile,
) -> Option<CompletionResponse> {
    let mut completions = Vec::new();

    // Add built-in functions
    for builtin in [BuiltinFn::Len, BuiltinFn::Matches, BuiltinFn::Min, BuiltinFn::Max, BuiltinFn::Between] {
        completions.push(CompletionItem {
            label: builtin.name().into(),
            kind: Some(CompletionItemKind::FUNCTION),
            detail: Some(format!("{} ({} args)", builtin.name(), builtin.arity())),
            documentation: Some(Documentation::MarkupContent(MarkupContent {
                kind: MarkupKind::MARKDOWN,
                value: builtin.docs().into(),
            })),
            ..Default::default()
        });
    }

    // Add existing guard declarations
    for (name, _) in &state.guard_symbols {
        completions.push(CompletionItem {
            label: name.clone(),
            kind: Some(CompletionItemKind::CONSTANT),
            detail: Some("Guard constraint".into()),
            ..Default::default()
        });
    }

    // Add target schema fields
    if let Some(schema) = &state.config.target_schema {
        for (field, ty) in &schema.fields {
            completions.push(CompletionItem {
                label: field.clone(),
                kind: Some(CompletionItemKind::FIELD),
                detail: Some(format!("Type: {ty}")),
                ..Default::default()
            });
        }
    }

    Some(CompletionResponse::Array(completions))
}
```

---

### 3.4 Go-to-Definition
Jump to the declaration of a referenced guard or field:
```rust
pub fn handle_goto_definition(
    state: &GuardLspState,
    params: GotoDefinitionParams,
    text: &str,
    ast: &GuardFile,
) -> Option<GotoDefinitionResponse> {
    let cursor_offset = lsp_pos_to_offset(params.text_document_position.position, text)?;
    let AstNode::Ref(name) = find_ast_node_at_offset(ast, cursor_offset)? else { return None };

    // Lookup global guard symbols
    state.guard_symbols.get(name).map(|loc| {
        GotoDefinitionResponse::Scalar(loc.clone())
    })
}
```

---

### 3.5 Code Actions
Quick fixes for common issues like undefined references or formatting:
```rust
pub fn handle_code_actions(
    state: &GuardLspState,
    params: CodeActionParams,
    diagnostics: &[Diagnostic],
) -> Vec<CodeActionOrCommand> {
    let mut actions = Vec::new();

    // Format document action
    actions.push(CodeActionOrCommand::CodeAction(CodeAction {
        title: "Format with guardfmt".into(),
        kind: Some(CodeActionKind::SOURCE_FORMAT),
        command: Some(Command {
            title: "Format".into(),
            command: "textDocument/formatting".into(),
            arguments: Some(vec![serde_json::to_value(&DocumentFormattingParams {
                text_document: params.text_document.clone(),
                options: Default::default(),
            }).unwrap()]),
            ..Default::default()
        }),
        ..Default::default()
    }));

    // Quick fix for undefined references
    for diag in diagnostics {
        if diag.code.as_ref().is_some_and(|c| c == &NumberOrString::String("undefined-ref".into())) {
            let symbol_name = diag.message.split('`').nth(1)?;
            actions.push(CodeActionOrCommand::CodeAction(CodeAction {
                title: format!("Create guard `{symbol_name}`").into(),
                kind: Some(CodeActionKind::QUICKFIX),
                edit: Some(WorkspaceEdit {
                    changes: Some(HashMap::from_iter([(
                        params.text_document.text_document.uri.clone(),
                        vec![TextEdit {
                            range: TextRange::new(Position::new(0,0), Position::new(0,0)),
                            new_text: format!("\nguard {symbol_name} {{ /* your constraint */ }}"),
                        }],
                    )])),
                    ..Default::default()
                }),
                ..Default::default()
            }));
        }
    }

    actions
}
```

---

### 3.6 Semantic Tokens
Syntax highlighting for the DSL:
```rust
pub const SEMANTIC_TOKEN_TYPES: &[&str] = &["keyword", "function", "string", "number", "operator", "comment"];
pub const SEMANTIC_TOKEN_MODIFIERS: &[&str] = &["declaration", "readonly"];

pub fn handle_semantic_tokens_full(
    state: &GuardLspState,
    _params: SemanticTokensFullParams,
    text: &str,
    ast: &GuardFile,
) -> Option<SemanticTokens> {
    if !state.config.enable_semantic_tokens { return None }

    let mut tokens = Vec::new();
    let mut last_line = 0;
    let mut last_char = 0;

    for guard in &ast.guards {
        // Highlight `guard` keyword
        add_semantic_token(&mut tokens, guard.span, text, 0, &mut last_line, &mut last_char, 0);
        // Highlight guard name
        add_semantic_token(&mut tokens, guard.span, text, 1, &mut last_line, &mut last_char, 0);
    }

    Some(SemanticTokens { result_id: None, data: tokens })
}

// Helper for LSP's relative semantic token format
fn add_semantic_token(tokens: &mut Vec<u32>, span: TextRange, text: &str, type_idx: usize, last_line: &mut u32, last_char: &mut u32, modifiers: u32) {
    let start = offset_to_lsp_pos(span.start, text);
    let end = offset_to_lsp_pos(span.end, text);
    let delta_line = start.line - *last_line;
    let delta_start = if delta_line == 0 { start.character - *last_char } else { start.character };

    tokens.extend([
        delta_line as u32,
        delta_start as u32,
        (end.character - start.character) as u32,
        type_idx as u32,
        modifiers,
    ]);

    *last_line = start.line;
    *last_char = start.character;
}
```

---

### 3.7 Inlay Hints
Inline parameter and type hints:
```rust
pub fn handle_inlay_hints(
    state: &GuardLspState,
    _params: InlayHintParams,
    text: &str,
    ast: &GuardFile,
) -> Option<Vec<InlayHint>> {
    if !state.config.enable_inlay_hints { return None }

    let mut hints = Vec::new();

    for guard in &ast.guards {
        // Add parameter hints for builtin calls
        if let Expr::BuiltinCall(builtin, args) = &guard.body {
            for (i, arg) in args.iter().enumerate() {
                let pos = offset_to_lsp_pos(arg.span().start, text);
                hints.push(InlayHint {
                    position: pos,
                    label: InlayHintLabel::String(format!("{}: ", builtin.arg_names()[i])),
                    kind: Some(InlayHintKind::PARAMETER),
                    ..Default::default()
                });
            }
        }

        // Add inline type hints
        let end_pos = offset_to_lsp_pos(guard.span.end, text);
        hints.push(InlayHint {
            position: end_pos,
            label: InlayHintLabel::String(format!(" -> {}", guard.target)),
            kind: Some(InlayHintKind::TYPE),
            ..Default::default()
        });
    }

    Some(hints)
}
```

---

## 4. Tooling: `guardfmt` and `guardlint`
### 4.1 `guardfmt`: DSL Formatter
```rust
#[derive(Debug, Error)]
pub enum GuardFmtError {
    #[error("Failed to spawn guardfmt: {0}")]
    SpawnError(#[from] std::io::Error),
    #[error("guardfmt failed: {0}")]
    ExecutionError(String),
}

pub fn guardfmt(text: &str, config: &GuardLspConfig) -> Result<String, GuardFmtError> {
    // Use custom binary if provided, else built-in formatter
    if let Some(path) = &config.guardfmt_path {
        let output = std::process::Command::new(path)
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn()?
            .wait_with_output()