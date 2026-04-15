# Changelog

## 2026-04-14

### Changed

- `AgentLoop` now owns a real `AgentSessionState` instead of exposing its internal trace array as the model context.
- `ModelClient` now reads a readonly `ModelContextView` with `sessionId`, `currentStep`, `messages`, `recentEvents`, and optional `metadata`.
- `ActionExecutor` now receives a minimal `ExecutionContext` alongside each `builtin_call`, so execution runs inside loop-owned session context without depending on mutable loop state.
- The demo and tests were updated to use the new state/view/execution-context split.
