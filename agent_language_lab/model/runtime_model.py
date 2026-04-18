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
    config = read_runtime_model_config(env)
    if config.mode == "demo":
        return DemoModel()

    raise NotImplementedError(
        "Python runtime dev mode is planned for Phase 2. "
        "Current Python implementation supports AGENT_MODEL_MODE=demo only."
    )
