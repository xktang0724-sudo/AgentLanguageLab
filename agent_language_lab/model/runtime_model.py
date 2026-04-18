from __future__ import annotations

from typing import Mapping

from agent_language_lab.agent.model_client import ModelClient
from agent_language_lab.demo.demo_model import DemoModel
from agent_language_lab.model.runtime_config import (
    ModelRuntimeEnvironment,
    read_runtime_model_config,
)


def create_runtime_model(
    env: ModelRuntimeEnvironment | None = None,
) -> ModelClient:
    # 根据配置模式返回具体模型客户端；当前仅 demo 走本地实现
    config = read_runtime_model_config(env)
    if config.mode == "demo":
        return DemoModel()

    # dev 模式保留到下一阶段，实现后可在此扩展真实 provider
    raise NotImplementedError(
        "Python runtime dev mode is planned for Phase 2. "
        "Current Python implementation supports AGENT_MODEL_MODE=demo only."
    )
