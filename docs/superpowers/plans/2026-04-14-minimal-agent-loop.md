# Minimal Agent Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 TypeScript 中实现一个最小可运行的 agent loop，基于 `ModelClient` 抽象完成决策与执行拆分，并用 `DemoModel + DemoExecutor` 跑通完整示例。

**Architecture:** 核心 loop 只依赖 `ModelClient` 和 `ActionExecutor` 两个接口。`AgentAction` 作为统一动作协议，当前支持 `final_answer` 和 `builtin_call`。通过结构化 `trace` 记录每次决策与执行结果，并用 `maxSteps` 控制循环上限。

**Tech Stack:** TypeScript, Node.js built-in test runner, `assert`, `tsc`

---

### Task 1: 建立最小 TypeScript 工程骨架

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`

- [ ] **Step 1: 创建最小工程配置**

```json
{
  "name": "agent-language-lab",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "test": "node --test dist/tests/**/*.test.js",
    "demo": "node dist/src/demo/run-demo.js"
  }
}
```

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "rootDir": ".",
    "outDir": "dist",
    "strict": true,
    "noEmitOnError": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*.ts", "tests/**/*.ts"]
}
```

- [ ] **Step 2: 运行构建验证空工程可编译**

Run: `npm run build`
Expected: PASS，生成 `dist/`

- [ ] **Step 3: 提交当前骨架**

```bash
git add package.json tsconfig.json
git commit -m "chore: add minimal typescript project skeleton"
```

### Task 2: 先写 AgentLoop 的失败测试

**Files:**
- Create: `tests/agent/agent-loop.test.ts`

- [ ] **Step 1: 写 direct final answer 的失败测试**

```ts
test("completes immediately when model returns final_answer", async () => {
  const result = await runAgentLoop({
    model: {
      decideNextAction: async () => ({
        type: "final_answer",
        answer: "done",
      }),
    },
    executor: {
      executeBuiltinCall: async () => {
        throw new Error("should not be called");
      },
    },
    userInput: "hello",
    maxSteps: 3,
  });

  assert.equal(result.status, "completed");
  assert.equal(result.answer, "done");
  assert.equal(result.steps, 0);
});
```

- [ ] **Step 2: 写 builtin_call -> final_answer 的失败测试**

```ts
test("executes builtin_call then completes with final_answer", async () => {
  let calls = 0;

  const result = await runAgentLoop({
    model: {
      decideNextAction: async () => {
        calls += 1;
        if (calls === 1) {
          return { type: "builtin_call", name: "echo", input: { text: "hello" } };
        }

        return { type: "final_answer", answer: "done after tool" };
      },
    },
    executor: {
      executeBuiltinCall: async (action) => ({
        ok: true,
        output: action.input,
      }),
    },
    userInput: "hello",
    maxSteps: 3,
  });

  assert.equal(result.status, "completed");
  assert.equal(result.answer, "done after tool");
  assert.equal(result.steps, 1);
  assert.equal(result.trace.length, 3);
});
```

- [ ] **Step 3: 写 maxSteps 的失败测试**

```ts
test("stops when maxSteps is exceeded without final_answer", async () => {
  const result = await runAgentLoop({
    model: {
      decideNextAction: async () => ({
        type: "builtin_call",
        name: "loop",
        input: {},
      }),
    },
    executor: {
      executeBuiltinCall: async () => ({
        ok: true,
        output: {},
      }),
    },
    userInput: "hello",
    maxSteps: 2,
  });

  assert.equal(result.status, "max_steps_exceeded");
  assert.equal(result.answer, null);
  assert.equal(result.steps, 2);
});
```

- [ ] **Step 4: 运行测试验证正确失败**

Run: `npm test`
Expected: FAIL，提示 `runAgentLoop` 或相关模块不存在

- [ ] **Step 5: 提交测试骨架**

```bash
git add tests/agent/agent-loop.test.ts
git commit -m "test: add failing tests for minimal agent loop"
```

### Task 3: 实现最小 agent 协议与 loop

**Files:**
- Create: `src/agent/types.ts`
- Create: `src/agent/model-client.ts`
- Create: `src/agent/action-executor.ts`
- Create: `src/agent/agent-loop.ts`
- Test: `tests/agent/agent-loop.test.ts`

- [ ] **Step 1: 定义协议类型**

```ts
export type FinalAnswerAction = {
  type: "final_answer";
  answer: string;
};

export type BuiltinCallAction = {
  type: "builtin_call";
  name: string;
  input: unknown;
};

export type AgentAction = FinalAnswerAction | BuiltinCallAction;

export type BuiltinResult = {
  ok: boolean;
  output: unknown;
};

export type AgentTraceItem =
  | {
      kind: "model_decision";
      action: AgentAction;
    }
  | {
      kind: "action_result";
      action: BuiltinCallAction;
      result: BuiltinResult;
    };

export type AgentLoopContext = {
  userInput: string;
  steps: number;
  trace: AgentTraceItem[];
};

export type AgentRunResult = {
  status: "completed" | "max_steps_exceeded";
  answer: string | null;
  steps: number;
  trace: AgentTraceItem[];
};
```

- [ ] **Step 2: 定义 model 和 executor 抽象**

```ts
export interface ModelClient {
  decideNextAction(context: AgentLoopContext): Promise<AgentAction>;
}
```

```ts
export interface ActionExecutor {
  executeBuiltinCall(action: BuiltinCallAction): Promise<BuiltinResult>;
}
```

- [ ] **Step 3: 写最小 loop 实现**

```ts
export async function runAgentLoop(input: RunAgentLoopInput): Promise<AgentRunResult> {
  const trace: AgentTraceItem[] = [];
  let steps = 0;

  while (steps < input.maxSteps) {
    const context: AgentLoopContext = {
      userInput: input.userInput,
      steps,
      trace,
    };

    const action = await input.model.decideNextAction(context);
    trace.push({ kind: "model_decision", action });

    if (action.type === "final_answer") {
      return {
        status: "completed",
        answer: action.answer,
        steps,
        trace,
      };
    }

    const result = await input.executor.executeBuiltinCall(action);
    trace.push({ kind: "action_result", action, result });
    steps += 1;
  }

  return {
    status: "max_steps_exceeded",
    answer: null,
    steps,
    trace,
  };
}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `npm run build && npm test`
Expected: PASS，三个 loop 测试全部通过

- [ ] **Step 5: 提交 loop 实现**

```bash
git add src/agent tests/agent/agent-loop.test.ts
git commit -m "feat: add minimal agent loop with structured trace"
```

### Task 4: 加入 DemoModel、DemoExecutor 和 demo 入口

**Files:**
- Create: `src/demo/demo-model.ts`
- Create: `src/demo/demo-executor.ts`
- Create: `src/demo/run-demo.ts`

- [ ] **Step 1: 先写 demo 的失败测试**

```ts
test("demo model and executor complete a full loop", async () => {
  const result = await runDemo("hello");

  assert.equal(result.status, "completed");
  assert.equal(result.answer, "Done: hello");
});
```

- [ ] **Step 2: 实现 DemoExecutor 的 registry**

```ts
type BuiltinHandler = (input: unknown) => Promise<unknown> | unknown;

export class DemoExecutor implements ActionExecutor {
  constructor(private readonly builtins: Record<string, BuiltinHandler>) {}

  async executeBuiltinCall(action: BuiltinCallAction): Promise<BuiltinResult> {
    const handler = this.builtins[action.name];
    if (!handler) {
      throw new Error(`Unknown builtin: ${action.name}`);
    }

    return {
      ok: true,
      output: await handler(action.input),
    };
  }
}
```

- [ ] **Step 3: 实现 DemoModel 和 runDemo**

```ts
export class DemoModel implements ModelClient {
  async decideNextAction(context: AgentLoopContext): Promise<AgentAction> {
    const lastResult = [...context.trace]
      .reverse()
      .find((item) => item.kind === "action_result");

    if (!lastResult) {
      return {
        type: "builtin_call",
        name: "echo",
        input: { text: context.userInput },
      };
    }

    return {
      type: "final_answer",
      answer: `Done: ${context.userInput}`,
    };
  }
}
```

- [ ] **Step 4: 运行 demo 验证完整流程**

Run: `npm run build && npm run demo`
Expected: 控制台输出完成状态、答案和 trace

- [ ] **Step 5: 提交 demo**

```bash
git add src/demo
git commit -m "feat: add demo model and executor for agent loop"
```

### Task 5: 最终验证

**Files:**
- Verify: `src/**/*.ts`
- Verify: `tests/**/*.ts`

- [ ] **Step 1: 运行完整验证**

Run: `npm run build`
Expected: PASS

Run: `npm test`
Expected: PASS

Run: `npm run demo`
Expected: PASS，并输出一个完整的 agent loop 运行结果

- [ ] **Step 2: 检查学习目标是否达成**

确认以下几点都能从代码中直接看出来：

- `ModelClient` 只做决策
- `ActionExecutor` 只做执行
- `generateResponse()` 已经被明确拆成决策和执行两个概念
- `AgentAction` 是统一协议
- `maxSteps` 和 `trace` 在 loop 中是第一类概念

- [ ] **Step 3: 提交最终状态**

```bash
git add .
git commit -m "feat: add minimal extensible agent loop example"
```
