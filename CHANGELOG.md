# Changelog

## 2026-04-15

### Changed

- `builtin_call` was replaced by `tool_call`, and tool actions now carry a stable `callId` plus `toolName` instead of an ad hoc builtin name.
- `AgentAction` now models non-tool control actions explicitly with `ask_user` and `handoff_to_human`, so clarification and escalation no longer need to masquerade as tools.
- `ActionExecutor` now executes `tool_call` against a `ToolRegistry`, validates `unknown` input through `ToolDefinition.validate()`, and returns a uniform `ToolObservation` instead of mutating loop-owned state.
- `ExecutionContext` is now readonly and carries execution-scoped data such as `traceId`, `userId`, `permissions`, and optional `metadata`; loop state remains owned by `AgentLoop`.
- `AgentLoop` now records `tool_observation` events, appends tool messages from observations, and separately tracks `modelCallCount` and `toolCallCount`; `AgentRunResult.steps` now reflects decision rounds.
- The demo was rewritten as a customer-service scenario with `lookupOrder` and `draftReply` tools plus non-tool `ask_user` and `handoff_to_human` paths.
- Tests were expanded to cover readonly snapshots, observation-based execution, decision/tool counters, clarification, human handoff, and the full customer-service loop.
- Added a runtime model layer with `AGENT_MODEL_MODE=demo|dev`, where `demo` keeps using `DemoModel` and `dev` switches to a `VercelAiModelClient`.
- Added `AGENT_MODEL_ID=<provider>:<model>` parsing plus provider-specific key validation for `OpenAI` and `Anthropic`.
- Added a Vercel AI SDK based model client that converts structured model output back into the existing `AgentAction` protocol instead of bypassing the loop or the tool executor.
- Added tests for runtime config parsing, structured action mapping, and a full dev-mode loop driven by an AI SDK mock model.
- Updated the README and architecture docs to document the new runtime selector and model integration path.
- Added automatic `.env.local` loading for the demo entrypoint plus a tracked `.env.local.example` template.
- Added optional model base URL overrides via `AGENT_MODEL_BASE_URL`, `OPENAI_BASE_URL`, and `ANTHROPIC_BASE_URL`.

## 2026-04-14

### Changed

- `AgentLoop` now owns a real `AgentSessionState` instead of exposing its internal trace array as the model context.
- `ModelClient` now reads a readonly `ModelContextView` with `sessionId`, `currentStep`, `messages`, `recentEvents`, and optional `metadata`.
- `ActionExecutor` now receives a minimal `ExecutionContext` alongside each `builtin_call`, so execution runs inside loop-owned session context without depending on mutable loop state.
- The demo and tests were updated to use the new state/view/execution-context split.
