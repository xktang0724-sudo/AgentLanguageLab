# Python Agent Loop Spec

**日期：** 2026-04-18

## 目标

当前仓库以 Python 作为唯一活跃实现，先完成一个最小可运行、便于学习的 agent loop 骨架。

## 当前范围

这次覆盖：

1. 核心 agent 协议
2. `run_agent_loop()`
3. `DemoModel`
4. `DemoExecutor`
5. `.env.local` 加载
6. `demo` 模式 runtime selector
7. Python 测试和 CLI

这次不覆盖：

- OpenAI / Anthropic SDK 接入
- 真实模型结构化输出
- provider resolver

## 设计原则

- 保持概念边界清晰，便于逐步学习
- Python 命名使用 snake_case
- 先把最核心的数据流跑通，再补真实模型接入
- 先用标准库实现，避免一开始就引入不必要依赖

## 代码布局规约

```text
agent_language_lab/
  agent/
  demo/
  model/
  shared/
python_tests/
```

规约：

- `agent/` 只放通用 agent 概念，不放 demo 业务逻辑
- `demo/` 只放客服场景的本地样例
- `model/` 只放 runtime 配置和模型选择逻辑
- `shared/` 只放跨模块通用但不属于 agent 领域本身的工具函数
- `python_tests/` 按用户视角验证行为，不围绕私有函数写碎测试

## 协议规约

动作语义：

- `final_answer`
- `ask_user`
- `handoff_to_human`
- `tool_call`

运行结果状态：

- `completed`
- `needs_user_input`
- `handoff_requested`
- `max_steps_exceeded`

实现规约：

- `run_agent_loop()` 是唯一状态推进者
- model 不直接执行工具
- executor 不决定下一步动作
- context 传递采用防御性快照，避免 loop 内状态被直接复用

## 工程规约

### 代码风格

- 优先 `dataclass` 和 `Protocol`
- 优先标准库
- 注释只解释边界和非直观点
- 单个模块尽量聚焦一个概念

### 错误处理

- 未知 tool 返回失败型 `ToolObservation`
- tool 校验或执行异常统一收敛为失败型 `ToolObservation`
- runtime mode 超出当前范围时明确抛出 `NotImplementedError`

### 测试

至少覆盖：

1. 直接 `final_answer`
2. `tool_call -> final_answer`
3. `max_steps_exceeded`
4. `ask_user`
5. `handoff_to_human`
6. 完整 demo loop
7. runtime config 默认值和当前边界

## 完成标准

满足以下条件即算完成：

1. `python -m unittest discover -s python_tests` 通过
2. `python -m agent_language_lab.demo.run_demo` 能输出 JSON 结果
3. 文档中已明确当前只完整支持 `demo` 模式
4. 目录和命名已经能自然承接真实模型接入
