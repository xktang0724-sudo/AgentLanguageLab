from __future__ import annotations

import asyncio
import json
import sys

from agent_language_lab.agent.agent_loop import RunAgentLoopInput, run_agent_loop
from agent_language_lab.agent.model_client import ModelClient
from agent_language_lab.agent.types import AgentRunResult
from agent_language_lab.demo.demo_executor import DemoExecutor
from agent_language_lab.model.load_env import load_runtime_env_files
from agent_language_lab.model.runtime_config import ModelRuntimeEnvironment
from agent_language_lab.model.runtime_model import create_runtime_model
from agent_language_lab.shared.serialization import to_jsonable


async def run_demo(
    user_input: str,
    *,
    env: ModelRuntimeEnvironment | None = None,
    model: ModelClient | None = None,
) -> AgentRunResult:
    load_runtime_env_files()
    selected_model = model or create_runtime_model(env)
    executor = DemoExecutor()

    return await run_agent_loop(
        RunAgentLoopInput(
            model=selected_model,
            executor=executor,
            user_input=user_input,
            max_steps=3,
            permissions=("orders:read",),
        )
    )


async def _print_demo() -> None:
    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Where is order ORD-1001?"
    result = await run_demo(user_input)
    print(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(_print_demo())
