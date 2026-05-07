# Agent Lifecycle Registry

**Design document only. Not yet implemented.**

This describes how agent lifecycle tracking would work in the fleet — registration, state management, health monitoring, and retirement across all Cocapn agents.

## Proposed Scope

- Agent registration and discovery
- Lifecycle state machine (create → configure → active → monitor → retire)
- Health tracking with auto-recovery signalling
- Single source of truth for fleet-wide agent state

Nothing here is running yet. When implementation starts, this repo will hold the spec, schema, and stubs.
