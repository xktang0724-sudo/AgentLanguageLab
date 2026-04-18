from __future__ import annotations

from typing import Protocol

from agent_language_lab.agent.types import AgentAction, ModelContextView


class ModelClient(Protocol):
    async def decide_next_action(self, context: ModelContextView) -> AgentAction:
        """Return the next single action for the agent loop."""
