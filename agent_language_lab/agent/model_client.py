from __future__ import annotations

from typing import Protocol

from agent_language_lab.agent.types import AgentAction, ModelContextView


# 模型客户端协议：每次只负责返回「下一步动作」
class ModelClient(Protocol):
    async def decide_next_action(self, context: ModelContextView) -> AgentAction:
        """基于当前上下文返回单一动作，由 agent_loop 统一消费。"""
