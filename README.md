# AgentLanguageLab

这是一个学习型实验仓库，用来逐步学习 AI agent 基础模式，以及它们在 Python 中的直接表达方式。

当前仓库包含：

- 一个最小可运行的 `agent loop`
- 基于 `ModelClient` 抽象做下一步决策
- `tool_call / ask_user / handoff_to_human / final_answer` 四类动作
- 结构化 `trace`
- 一个客服场景 demo
- 一个 Python runtime model 选择层
  - `demo` 模式走本地 `DemoModel`
  - `dev` 模式配置已解析，但真实模型接入留到后续阶段

## 当前目录

```text
agent_language_lab/
  agent/
    types.py
    model_client.py
    action_executor.py
    agent_loop.py
  demo/
    demo_model.py
    demo_executor.py
    tool_catalog.py
    run_demo.py
  model/
    load_env.py
    runtime_config.py
    runtime_model.py
  shared/
    serialization.py
python_tests/
  test_agent_loop.py
docs/
  architecture/
    INDEX.md
    v0.0.5/
      README.md
      python-agent-loop-architecture.svg
```

## 运行环境

需要 Python 3.11+。

当前实现只使用标准库，不需要安装第三方依赖。项目启动时会自动读取根目录下的 `.env.local`。

## 模型模式

模型接入层由 `AGENT_MODEL_MODE` 控制：

- `demo`
  - 默认值
  - 忽略真实模型配置
  - 直接使用本地 `DemoModel`
- `dev`
  - 当前会读取并校验 provider 配置
  - 真实模型 client 尚未接入
  - 调用运行入口时会明确抛出 Phase 2 未实现

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
2. 先保持 `AGENT_MODEL_MODE=demo`
3. 运行 Python demo

## 如何启动

运行默认 demo：

```bash
python -m agent_language_lab.demo.run_demo
```

指定输入：

```bash
python -m agent_language_lab.demo.run_demo "Where is order ORD-1001?"
```

这会：

1. 读取 `.env.local`
2. 创建 `DemoModel`
3. 创建 `DemoExecutor`
4. 调用 `run_agent_loop()`
5. 输出最终结果 JSON

## 当前实现边界

当前 Python 版本已经完成最小可运行路径：

- `ModelClient` 负责决策
- `ActionExecutor` 负责执行 tool call
- `run_agent_loop()` 负责状态推进
- `DemoModel + DemoExecutor` 跑通客服场景
- 运行结果和 trace 可序列化为 JSON

当前暂不包含：

- 真实模型 SDK 接入
- 结构化真实模型输出校验
- provider resolver
- 多轮会话恢复

## 当前 demo 行为

- 缺订单号时，返回 `ask_user`
- 输入包含 `chargeback / fraud / lawyer / legal` 时，返回 `handoff_to_human`
- 正常订单查询时，模型先发出 `lookupOrder`
- 拿到订单 observation 后，再发出 `draftReply`
- 拿到回复草稿 observation 后，返回 `final_answer`

示例输出会类似这样：

```json
{
  "status": "completed",
  "answer": "Your order ORD-1001 has shipped and is expected to arrive by 2026-04-18.",
  "question": null,
  "handoff_reason": null,
  "steps": 3,
  "model_call_count": 3,
  "tool_call_count": 2
}
```

## 如何测试

```bash
python -m unittest discover -s python_tests
```

当前测试覆盖：

- loop 的终止、上下文快照和 trace 行为
- `tool_call -> observation -> final_answer`
- `max_steps_exceeded`
- `ask_user`
- `handoff_to_human`
- 完整客服 demo
- runtime config 默认值、provider 校验和当前 Phase 2 边界

## 建议阅读顺序

1. `agent_language_lab/demo/run_demo.py`
2. `agent_language_lab/model/runtime_model.py`
3. `agent_language_lab/demo/demo_model.py`
4. `agent_language_lab/demo/demo_executor.py`
5. `agent_language_lab/agent/agent_loop.py`
6. `agent_language_lab/agent/types.py`

## 当前架构文档

架构文档在这里：

- [docs/architecture/INDEX.md](./docs/architecture/INDEX.md)
- [docs/architecture/v0.0.5/README.md](./docs/architecture/v0.0.5/README.md)

架构图文件在这里：

- [docs/architecture/v0.0.5/python-agent-loop-architecture.svg](./docs/architecture/v0.0.5/python-agent-loop-architecture.svg)

## 下一步可以做什么

- 补 Python 真实模型 client
- 给模型决策 prompt 加更细的 guardrails
- 给 tool schema 做更强的共享类型约束
- 引入 memory / RAG
- 把 demo 场景扩展成多轮用户输入
