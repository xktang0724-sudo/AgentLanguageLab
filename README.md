# AgentLanguageLab

这是一个学习型实验仓库，用来逐步学习 AI 编程语法、AI agent 基础模式，以及它们在 TypeScript / JavaScript / Python 中的表达方式。

当前仓库的最小示例已经包含：

- 一个最小可运行的 `agent loop`
- 基于 `ModelClient` 抽象做下一步决策
- `tool_call / ask_user / handoff_to_human / final_answer` 四类动作
- 结构化 `trace`
- 一个客服场景 demo
- 一个可切换的模型接入层
  - `demo` 模式走本地 `DemoModel`
  - `dev` 模式走 `Vercel AI SDK`

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
    demo-tool-catalog.ts
    run-demo.ts
  model/
    runtime-config.ts
    runtime-model.ts
    vercel-ai-model-client.ts
tests/
  agent/
    agent-loop.test.ts
    model-runtime.test.ts
docs/
  architecture/
    INDEX.md
    v0.0.4/
      README.md
      model-runtime-agent-loop-architecture.svg
```

## 运行环境

需要本机有这些工具：

- Node.js
- npm

安装依赖：

```bash
npm install
```

项目启动时会自动读取根目录下的 `.env.local`。

## 模型模式

模型接入层由 `AGENT_MODEL_MODE` 控制：

- `demo`
  - 默认值
  - 忽略真实模型配置
  - 直接使用本地 `DemoModel`
- `dev`
  - 接入 `Vercel AI SDK`
  - 当前内置支持 `OpenAI` 和 `Anthropic`
  - 模型仍然输出结构化 `AgentAction`
  - 工具执行仍然走本地 `DemoExecutor`

### 环境变量

```text
AGENT_MODEL_MODE=demo | dev
AGENT_MODEL_ID=<provider>:<model-name>
AGENT_MODEL_BASE_URL=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

推荐做法：

1. 复制 `.env.local.example` 为 `.env.local`
2. 按你的模型配置修改
3. 直接运行 `npm run demo`

约束：

- `AGENT_MODEL_MODE` 默认是 `demo`
- `AGENT_MODEL_MODE=dev` 时必须设置 `AGENT_MODEL_ID`
- `AGENT_MODEL_ID` 当前只支持：
  - `openai:<model-name>`
  - `anthropic:<model-name>`
- 选中哪个 provider，就必须提供对应的 API key
- 如果你要走代理、中转或自建网关，可以额外设置：
  - `AGENT_MODEL_BASE_URL`
  - 或 provider 专属别名 `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL`

## 如何启动

### 1. 编译

```bash
npm run build
```

### 2. 运行 demo 模式

```bash
npm run demo
```

这会：

1. 读取 `AGENT_MODEL_MODE`
2. 默认创建 `DemoModel`
3. 创建 `DemoExecutor`
4. 调用 `runAgentLoop()`
5. 输出最终结果 JSON

### 3. 运行 dev 模式

先创建配置文件：

```bash
cp .env.local.example .env.local
```

把 `.env.local` 改成你要的模式。

最小 `demo` 配置：

```text
AGENT_MODEL_MODE=demo
```

OpenAI 配置：

```text
AGENT_MODEL_MODE=dev
AGENT_MODEL_ID=openai:gpt-4.1
OPENAI_API_KEY=your-openai-key
AGENT_MODEL_BASE_URL=https://your-openai-compatible-gateway/v1
```

Anthropic 配置：

```text
AGENT_MODEL_MODE=dev
AGENT_MODEL_ID=anthropic:claude-sonnet-4-5
ANTHROPIC_API_KEY=your-anthropic-key
AGENT_MODEL_BASE_URL=https://your-anthropic-gateway.example.com
```

OpenAI 示例：

```bash
npm run demo
```

Anthropic 示例：

```bash
npm run demo
```

`dev` 模式下的数据流是：

1. `runDemo()` 根据环境变量创建 runtime model
2. `VercelAiModelClient` 读取当前 `ModelContextView`
3. 模型通过结构化输出返回一个 `AgentAction`
4. 如果是 `tool_call`，仍由本地 `DemoExecutor` 执行 `lookupOrder` / `draftReply`
5. loop 继续推进直到 `completed`、`needs_user_input`、`handoff_requested` 或 `max_steps_exceeded`

如果你没有设置调用地址，OpenAI 和 Anthropic 会默认走各自官方地址。

## 如何接入我的模型

如果你的模型就在 `OpenAI` 或 `Anthropic` 体系内，只需要两步：

1. 在 `.env.local` 里选一个 `AGENT_MODEL_ID`
2. 在 `.env.local` 里设置对应 provider 的 API key

例如：

```bash
cp .env.local.example .env.local
```

然后把 `.env.local` 改成：

```text
AGENT_MODEL_MODE=dev
AGENT_MODEL_ID=openai:gpt-4.1-mini
OPENAI_API_KEY=your-openai-key
AGENT_MODEL_BASE_URL=https://your-openai-compatible-gateway/v1
```

再运行：

```bash
npm run demo
```

如果你要接新的 provider，当前落点在：

- `src/model/runtime-config.ts`
- `src/model/runtime-model.ts`
- `src/model/vercel-ai-model-client.ts`

扩展方式是：

1. 在 `runtime-config.ts` 扩展支持的 provider 前缀
2. 在 `runtime-model.ts` 增加对应的 AI SDK provider resolver
3. 保持 `VercelAiModelClient` 输出的仍然是统一 `AgentAction`

也就是说，新 provider 只改模型接入层，不需要改 `agent-loop` 和工具执行层。

## 当前 demo 行为

- 缺订单号时，返回 `ask_user`
- 输入包含 `chargeback / fraud / lawyer / legal` 时，返回 `handoff_to_human`
- 正常订单查询时，模型先发出 `lookupOrder`
- 拿到订单 observation 后，再发出 `draftReply`
- 拿到回复草稿 observation 后，返回 `final_answer`

默认 demo 模式的示例输出会类似这样：

```json
{
  "status": "completed",
  "answer": "Your order ORD-1001 has shipped and is expected to arrive by 2026-04-18.",
  "question": null,
  "handoffReason": null,
  "steps": 3,
  "modelCallCount": 3,
  "toolCallCount": 2
}
```

## 如何测试

```bash
npm run build
npm test
```

当前测试覆盖了这些行为：

- loop 的终止、只读上下文和 trace 行为
- `DemoModel + DemoExecutor` 的完整客服流程
- `AGENT_MODEL_MODE` 和 `AGENT_MODEL_ID` 的配置解析
- `VercelAiModelClient` 的结构化输出映射
- `dev` 模式下真实模型 client 与本地工具链的端到端联动

## 如何调试

先编译：

```bash
npm run build
```

再调试编译后的入口：

```bash
RUN_AGENT_DEMO=true node --inspect-brk dist/src/demo/run-demo.js
```

如果你要调试 `dev` 模式，额外带上模型环境变量，例如：

```bash
AGENT_MODEL_MODE=dev \
AGENT_MODEL_ID=openai:gpt-4.1 \
OPENAI_API_KEY=your-openai-key \
RUN_AGENT_DEMO=true \
node --inspect-brk dist/src/demo/run-demo.js
```

当前更适合下断点的文件：

- `dist/src/demo/run-demo.js`
- `dist/src/model/runtime-model.js`
- `dist/src/model/vercel-ai-model-client.js`
- `dist/src/agent/agent-loop.js`

## 建议阅读顺序

建议按这个顺序看：

1. `src/demo/run-demo.ts`
2. `src/model/runtime-model.ts`
3. `src/model/vercel-ai-model-client.ts`
4. `src/demo/demo-model.ts`
5. `src/demo/demo-executor.ts`
6. `src/agent/agent-loop.ts`
7. `src/agent/types.ts`

## 当前架构文档

架构文档在这里：

- [docs/architecture/INDEX.md](./docs/architecture/INDEX.md)
- [docs/architecture/v0.0.4/README.md](./docs/architecture/v0.0.4/README.md)

架构图文件在这里：

- [docs/architecture/v0.0.4/model-runtime-agent-loop-architecture.svg](./docs/architecture/v0.0.4/model-runtime-agent-loop-architecture.svg)

## 下一步可以做什么

- 给 `VercelAiModelClient` 增加更多 provider
- 给模型决策 prompt 加更细的 guardrails
- 给 tool schema 做更强的共享类型约束
- 引入 memory / RAG
- 把 demo 场景扩展成多轮用户输入
