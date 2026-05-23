# Spreader-Tool Integration Assessment

**Repo:** https://github.com/SuperInstance/spreader-tool  
**Evaluated:** 2026-05-17  
**Verdict:** ⚠️ Interesting architecture, but **not ready for production use as-is**

---

## What It Is

Spreader-tool is a TypeScript multi-agent orchestration framework. You give it a research question, configure N "specialist" agents (researcher, analyst, synthesizer, coder, architect, critic, world-builder), and it:

1. Distributes full parent context to each specialist
2. Executes them (sequentially with handoffs or parallel in batches)
3. Passes "Ralph Wiggum" summaries between specialists ("what I did, what I found, what you need to know")
4. Compacts context when threads get long (recursive/summary/both strategies)
5. Synthesizes a final markdown report

It includes an in-process `AgentMessageBus` for agent-to-agent communication with request/response, broadcast, and error handling patterns.

## What Works

- ✅ **TypeScript compiles clean** — `tsc --noEmit` passes with zero errors
- ✅ **72/73 tests pass** (1 skipped) — communication utilities, message bus, progress callbacks
- ✅ **Well-structured types** — `SpreadConfig`, `SpecialistResult`, `FullContext`, `ProgressUpdate` are all solid interfaces
- ✅ **Provider abstraction** — clean `LLMProvider` interface with OpenAI, Anthropic, and Ollama implementations
- ✅ **Progress callback system** — real-time stage/specialist/token tracking
- ✅ **Context compaction** — recursive, summary, and combined strategies with token estimation
- ✅ **Agent communication** — full message bus with directed messaging, broadcasting, request-response, metrics
- ✅ **No hardcoded secrets** — clean

## What's Missing / Weak

### Critical
- **No actual API calls in providers** — the OpenAI/Anthropic/Ollama provider implementations are stubs. They define interfaces but don't actually call any API. The `complete()` method pattern exists but returns nothing real. You'd need to wire up actual HTTP calls.
- **No published npm package** — `@cocapn/spreader-tool` in the README doesn't exist on npm. This is a workspace-only tool.
- **No dist/ directory** — requires build before use, no prebuilt artifacts

### Moderate
- **CLI is skeleton** — `src/cli/` has init/config/run/list/status/results commands but they're config-driven stubs, not wired to the engine
- **No streaming** — provider interface declares `streamComplete()` but no implementation
- **Token counting is naive** — `Math.ceil(text.length / 4)` character estimation, not actual tokenization
- **No persistence** — spread results are in-memory only, no database/file tracking beyond the output directory
- **Summary synthesis is template-based** — `synthesizeResults()` just concatenates markdown, doesn't use an LLM to actually synthesize

### Minor
- **7 commits total** — very young project
- **17 npm vulnerabilities** (8 moderate, 9 high) in dependencies
- **DOCKSIDE-EXAM.md has no boxes checked** — self-certification not completed
- **Engine executes specialists sequentially by default** despite claiming parallel support (parallel path exists in coordinator but engine uses sequential with handoffs)

## Architecture Review

The architecture is actually good:

```
SpreaderEngine (orchestrator)
  ├── ContextManager (compact/distribute)
  ├── SpecialistCoordinator (execute agents)
  │   ├── Specialist (per-agent executor)
  │   └── ProviderRegistry (LLM backends)
  ├── RalphWiggumSummarizer (handoff summaries)
  └── AgentMessageBus (inter-agent communication)
```

The "Ralph Wiggum" handoff pattern is clever — each specialist gets a structured summary of what the previous one did, found, and what the next one needs to know. This is genuinely useful for multi-step research pipelines.

The `FullContext` distribution model (every specialist gets the full parent conversation, compacted if needed) is the right approach for maintaining coherence across agents.

## Integration Potential

### What we could use it for:
- **Research spread pipelines** — throw a question at 3-5 specialists, get a synthesized report
- **Multi-perspective code review** — architect + coder + critic agents on the same codebase
- **Parallel analysis tasks** — anything that benefits from multiple viewpoints

### What we'd need to do:
1. **Wire up actual providers** — make OpenAI/Anthropic/Ollama providers call real APIs
2. **Add our z.ai provider** — implement `LLMProvider` for the fleet's GLM models
3. **Fix the CLI** — make `spreader run` actually work end-to-end
4. **Add real tokenization** — use tiktoken or equivalent
5. **Add LLM-powered synthesis** — replace template concatenation with actual model summarization

## Bottom Line

**Score: 5/10 — good bones, no meat.**

The architecture and types are solid. The handoff pattern and context compaction are genuinely useful ideas. But the providers don't call APIs, the CLI doesn't work, and the synthesis is cosmetic. It's a well-designed skeleton that needs 2-3 days of wiring before it's useful.

**Recommendation:** Worth forking if we want a TypeScript multi-agent framework. Not worth using as-is — we'd be building the actual functionality on top of the type definitions. If we need this capability *now*, we're better off building directly on OpenAI/Anthropic SDKs with our own orchestration.

The `AgentMessageBus` and communication types are the most immediately reusable pieces — those could be extracted as a standalone package for fleet inter-agent communication.
