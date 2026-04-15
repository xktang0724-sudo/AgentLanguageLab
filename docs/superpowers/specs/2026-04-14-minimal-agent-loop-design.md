# Minimal Agent Loop Design

**日期：** 2026-04-14

## 目标

在 TypeScript 中实现一个最小可运行的 agent loop，用来清晰展示：

- 基于 `ModelClient` 抽象做下一步决策
- 把原本的 `generateResponse()` 思路拆成：
  - `decideNextAction()`
  - `executeAction()`
- 引入 `AgentAction` 联合类型
- 当前至少支持：
  - `final_answer`
  - `builtin_call`
- 支持 `maxSteps`
- 支持结构化 `trace`
- 先不接真实模型，使用 `DemoModel + DemoExecutor` 跑通骨架

这个示例优先服务学习，不追求生产级抽象完备度。

## 设计原则

- 先跑通最小 loop，再逐步叠加能力
- 抽象边界清楚，但不过度设计
- 保持命名贴近 agent 概念
- trace 先结构化，便于后续扩展调试、回放和可视化

## 核心角色

### ModelClient

职责：基于当前上下文，决定 agent 下一步动作。

```ts
interface ModelClient {
  decideNextAction(context: AgentLoopContext): Promise<AgentAction>;
}
```

它不负责执行工具，也不负责控制 loop。

### ActionExecutor

职责：执行 `builtin_call` 动作。

```ts
interface ActionExecutor {
  executeBuiltinCall(action: BuiltinCallAction): Promise<BuiltinResult>;
}
```

它不负责决定下一步，也不负责终止 loop。

### AgentLoop

职责：

- 驱动步骤推进
- 调用 `model.decideNextAction()`
- 调用 `executor.executeBuiltinCall()`
- 记录 `trace`
- 管理 `maxSteps`
- 在拿到 `final_answer` 时终止

### AgentAction

职责：作为 loop 的统一动作协议。

```ts
type AgentAction =
  | { type: "final_answer"; answer: string }
  | { type: "builtin_call"; name: string; input: unknown };
```

当前只保留两个最小分支，后续可以扩展更多动作类型。

## 最小数据结构

### BuiltinResult

```ts
type BuiltinResult = {
  ok: boolean;
  output: unknown;
};
```

### AgentTraceItem

```ts
type AgentTraceItem =
  | { kind: "model_decision"; action: AgentAction }
  | { kind: "action_result"; action: BuiltinCallAction; result: BuiltinResult };
```

trace 不使用纯字符串，而是保留结构化事件，方便后续扩展。

### AgentLoopContext

```ts
type AgentLoopContext = {
  userInput: string;
  steps: number;
  trace: AgentTraceItem[];
};
```

这个上下文先保持最小，只包含：

- 用户输入
- 已执行步数
- 历史 trace

后续可以自然叠加 memory、system prompt、压缩后的历史摘要等信息。

### AgentRunResult

```ts
type AgentRunResult = {
  status: "completed" | "max_steps_exceeded";
  answer: string | null;
  steps: number;
  trace: AgentTraceItem[];
};
```

返回统一运行结果，而不是直接返回字符串，便于调用方判断是否正常完成。

## Loop 数据流

1. 初始化 context
2. 调用 `model.decideNextAction(context)`
3. 记录 `model_decision`
4. 如果动作是 `final_answer`
   - 立即返回 `completed`
5. 如果动作是 `builtin_call`
   - 调用 `executor.executeBuiltinCall(action)`
   - 记录 `action_result`
   - 步数加一
   - 继续下一轮
6. 如果达到 `maxSteps` 仍未得到 `final_answer`
   - 返回 `max_steps_exceeded`

这里的 step 定义为“一轮模型决策及其后续处理”。对于 `builtin_call` 分支，一次决策和一次执行合并算 1 step，这样概念更稳定。

## Demo 设计

### DemoModel

不模拟真实推理，只做可预测的最小决策逻辑：

- 当 trace 中还没有 `action_result` 时：
  - 返回一个 `builtin_call`
- 当已经拿到 builtin 结果后：
  - 返回一个 `final_answer`

示例流程：

1. 用户输入 `"hello"`
2. `DemoModel` 返回：

```ts
{ type: "builtin_call", name: "echo", input: { text: "hello" } }
```

3. `DemoExecutor` 执行后返回：

```ts
{ ok: true, output: { echoed: "hello" } }
```

4. `DemoModel` 根据 trace 返回：

```ts
{ type: "final_answer", answer: "Done: hello" }
```

### DemoExecutor

采用最小注册表形式：

```ts
type BuiltinHandler = (input: unknown) => Promise<unknown> | unknown;
type BuiltinRegistry = Record<string, BuiltinHandler>;
```

这样即使当前只有 `echo` 一个 builtin，也已经具备可扩展结构，后续新增内置动作时不需要修改 loop。

## 文件结构

```text
docs/superpowers/specs/2026-04-14-minimal-agent-loop-design.md
docs/superpowers/plans/2026-04-14-minimal-agent-loop.md
package.json
tsconfig.json
src/agent/types.ts
src/agent/model-client.ts
src/agent/action-executor.ts
src/agent/agent-loop.ts
src/demo/demo-model.ts
src/demo/demo-executor.ts
src/demo/run-demo.ts
tests/agent/agent-loop.test.ts
```

## 测试策略

按 TDD 先围绕 `AgentLoop` 行为写测试，最少覆盖：

1. model 直接返回 `final_answer` 时应立即完成
2. model 先返回 `builtin_call`、再返回 `final_answer` 时应正确推进并记录 trace
3. model 一直返回 `builtin_call` 时应在 `maxSteps` 后停止
4. demo 入口能够跑通一个完整示例

## 错误处理边界

这版最小骨架不额外引入复杂错误分类系统。

- 未知 builtin 名称：由 `DemoExecutor` 抛出明确错误
- loop 不吞掉执行异常：直接让异常抛出，便于学习时看清失败位置

后续如果要向更完整 agent 演进，再增加：

- `action_error` trace
- executor 错误包装
- retry / reflection / fallback

## 为什么这是“最小但可堆叠”的设计

- 最小：角色只有 model、executor、loop、action 四层
- 可堆叠：更多 action、真实模型、memory、tool schema 都可以在现有边界上继续叠加
- 学习友好：每个文件只承载一个核心概念，便于横向对比和逐步扩展
