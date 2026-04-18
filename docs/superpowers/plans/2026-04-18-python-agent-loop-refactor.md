# Python Agent Loop Plan

**Goal:** 收敛为 Python 单实现，并保留一个最小可运行、便于学习的 agent loop 骨架。

**Architecture:** 保持 `ModelClient -> AgentAction -> ActionExecutor -> AgentLoop` 的概念边界不变。当前先跑通本地 demo，真实模型接入延后到后续 phase。

**Tech Stack:** Python 3.11+, standard library (`dataclasses`, `typing`, `unittest`, `json`, `copy`, `pathlib`, `uuid`)

---

## Phase 1: 最小 Python Agent Loop

**目标：** 跑通最小客服 demo，并把核心抽象稳定下来。

- [x] 新建 Python 包结构 `agent_language_lab/`
- [x] 定义动作协议、上下文、trace 和运行结果
- [x] 实现 `ModelClient` / `ActionExecutor` / `ToolRegistry`
- [x] 实现 `run_agent_loop()`
- [x] 实现 `DemoModel + DemoExecutor + run_demo()`
- [x] 增加 Python 测试并跑通

## Phase 2: Python Runtime Model 接入

**目标：** 在不改动 loop 和 executor 边界的前提下，补上真实模型 client。

- [ ] 保持 `demo | dev` 双模式
- [ ] 实现真实模型 client
- [ ] 保持真实模型只负责返回统一动作，不直接接管 loop
- [ ] 增加 provider 配置与结构化输出校验

## Phase 3: 更高层能力

**目标：** 在 Python 骨架稳定后再扩更多 agent 能力。

- [ ] memory / RAG
- [ ] workflow / multi-agent
- [ ] 更通用的 tool schema
- [ ] trace replay / debug 视图
