# AgentLanguageLab

这是一个学习型实验仓库，用来逐步学习 AI 编程语法、AI agent 基础模式，以及它们在 TypeScript / JavaScript / Python 中的表达方式。

当前仓库已经落地的第一个最小示例是：

- 一个最小可运行的 `agent loop`
- 基于 `ModelClient` 抽象做下一步决策
- 把原本的响应生成逻辑拆成：
  - `decideNextAction()`
  - `executeBuiltinCall()`
- loop 内部持有 `AgentSessionState`
- model 只拿到只读的 `ModelContextView`
- executor 只拿到最小 `ExecutionContext`
- 支持 `AgentAction`
  - `final_answer`
  - `builtin_call`
- 支持 `maxSteps`
- 支持结构化 `trace`
- 使用 `DemoModel + DemoExecutor` 跑通完整骨架

## 当前目录

```text
src/
  agent/
    types.ts
    model-client.ts
    action-executor.ts
    agent-loop.ts
  demo/
    demo-model.ts
    demo-executor.ts
    run-demo.ts
tests/
  agent/
    agent-loop.test.ts
docs/
  architecture/
    INDEX.md
    v0.0.1/
      README.md
      minimal-agent-loop-architecture.svg
```

## 运行环境

当前项目很轻，没有额外 npm 依赖，但需要本机有这些工具：

- Node.js
- npm
- TypeScript 编译器 `tsc`

如果你本机执行 `tsc --version` 有输出，就可以直接按下面步骤运行。

## 如何启动

### 1. 编译

```bash
npm run build
```

这会把 TypeScript 编译到 `dist/`。

### 2. 运行 demo

```bash
npm run demo
```

当前 demo 会执行：

1. 创建 `DemoModel`
2. 创建 `DemoExecutor`
3. 调用 `runAgentLoop()`
4. 输出最终结果 JSON

预期你会看到类似输出：

```json
{
  "status": "completed",
  "answer": "Done: hello",
  "steps": 1,
  "trace": [
    {
      "kind": "model_decision",
      "action": {
        "type": "builtin_call",
        "name": "echo",
        "input": {
          "text": "hello"
        }
      }
    },
    {
      "kind": "action_result",
      "action": {
        "type": "builtin_call",
        "name": "echo",
        "input": {
          "text": "hello"
        }
      },
      "result": {
        "ok": true,
        "output": {
          "text": "hello"
        }
      }
    },
    {
      "kind": "model_decision",
      "action": {
        "type": "final_answer",
        "answer": "Done: hello"
      }
    }
  ]
}
```

## 如何测试

先编译，再运行测试：

```bash
npm run build
npm test
```

当前测试覆盖了这些行为：

- model 直接返回 `final_answer`
- model 先返回 `builtin_call`，再返回 `final_answer`
- 一直没有 `final_answer` 时，loop 在 `maxSteps` 后停止
- model 收到的是只读快照视图，executor 收到的是最小执行上下文
- `DemoModel + DemoExecutor` 能跑通完整示例

## 如何调试

当前最直接的调试方式，是先编译，再调试 `dist/` 里的编译结果。

原因是现在项目还没有配置 source map，所以最稳定的方式是先看编译后的 JS 行为。

### 方式 1：命令行调试

先编译：

```bash
npm run build
```

再用 Node 调试 demo：

```bash
RUN_AGENT_DEMO=true node --inspect-brk dist/src/demo/run-demo.js
```

然后你可以：

- 打开 Chrome 的 `chrome://inspect`
- 或者用支持 Node Inspector 的 IDE 连接进程

### 方式 2：WebStorm 调试

如果你在用 WebStorm，建议这样配：

1. 先运行一次：

```bash
npm run build
```

2. 新建一个 `Node.js` 运行配置
3. `JavaScript file` 选择：

```text
dist/src/demo/run-demo.js
```

4. 添加环境变量：

```text
RUN_AGENT_DEMO=true
```

5. 直接点击 Debug

当前更适合在这些文件里下断点看逻辑：

- `dist/src/demo/run-demo.js`
- `dist/src/demo/demo-model.js`
- `dist/src/demo/demo-executor.js`
- `dist/src/agent/agent-loop.js`

## 建议阅读顺序

如果你想按理解成本最低的顺序看代码，建议这样读：

1. `src/demo/run-demo.ts`
2. `src/demo/demo-model.ts`
3. `src/demo/demo-executor.ts`
4. `src/agent/agent-loop.ts`
5. `src/agent/types.ts`

## 当前架构文档

架构文档在这里：

- [docs/architecture/INDEX.md](./docs/architecture/INDEX.md)
- [docs/architecture/v0.0.1/README.md](./docs/architecture/v0.0.1/README.md)

架构图文件在这里：

- [docs/architecture/v0.0.1/minimal-agent-loop-architecture.svg](./docs/architecture/v0.0.1/minimal-agent-loop-architecture.svg)

## 下一步可以做什么

这个最小骨架已经适合继续往上叠加。下一步常见方向有：

- 把 `DemoModel` 换成真实模型 client
- 给 `builtin_call` 增加 schema 或更强的类型约束
- 增加更多 action 类型
- 引入 memory
- 给调试链路补 source map，直接在 TypeScript 源码上断点
