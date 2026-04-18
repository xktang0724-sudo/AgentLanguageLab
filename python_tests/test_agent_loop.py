from __future__ import annotations

import os
import types
import unittest
from unittest.mock import patch

from agent_language_lab.agent.agent_loop import RunAgentLoopInput, run_agent_loop
from agent_language_lab.agent.types import (
    AgentAction,
    AskUserAction,
    ExecutionContext,
    FinalAnswerAction,
    HandoffToHumanAction,
    ModelContextView,
    ToolCallAction,
    ToolObservation,
)
from agent_language_lab.demo.demo_model import DemoModel
from agent_language_lab.demo.run_demo import run_demo
from agent_language_lab.model.runtime_config import (
    DemoRuntimeModelConfig,
    DevRuntimeModelConfig,
    read_runtime_model_config,
)
from agent_language_lab.model.runtime_model import create_runtime_model


class AgentLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_completes_immediately_when_model_returns_final_answer(self) -> None:
        class FinalAnswerModel:
            async def decide_next_action(self, context: ModelContextView) -> AgentAction:
                return FinalAnswerAction(answer="done")

        class FailingExecutor:
            async def execute_tool_call(
                self,
                action: ToolCallAction,
                context: ExecutionContext,
            ) -> ToolObservation:
                raise AssertionError("should not be called")

        result = await run_agent_loop(
            RunAgentLoopInput(
                model=FinalAnswerModel(),
                executor=FailingExecutor(),
                user_input="hello",
                max_steps=3,
            )
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.answer, "done")
        self.assertIsNone(result.question)
        self.assertIsNone(result.handoff_reason)
        self.assertEqual(result.steps, 1)
        self.assertEqual(result.model_call_count, 1)
        self.assertEqual(result.tool_call_count, 0)
        self.assertEqual(len(result.trace), 1)
        self.assertEqual(result.trace[0].kind, "model_decision")

    async def test_executes_tool_call_then_completes_with_final_answer(self) -> None:
        class ToolThenFinalModel:
            def __init__(self) -> None:
                self.calls = 0

            async def decide_next_action(self, context: ModelContextView) -> AgentAction:
                self.calls += 1
                if self.calls == 1:
                    return ToolCallAction(
                        call_id="call-1",
                        tool_name="echo",
                        input={"text": "hello"},
                    )

                return FinalAnswerAction(answer="done after tool")

        class EchoExecutor:
            async def execute_tool_call(
                self,
                action: ToolCallAction,
                context: ExecutionContext,
            ) -> ToolObservation:
                return ToolObservation(
                    call_id=action.call_id,
                    tool_name=action.tool_name,
                    ok=True,
                    output=action.input,
                )

        result = await run_agent_loop(
            RunAgentLoopInput(
                model=ToolThenFinalModel(),
                executor=EchoExecutor(),
                user_input="hello",
                max_steps=3,
            )
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.answer, "done after tool")
        self.assertEqual(result.steps, 2)
        self.assertEqual(result.model_call_count, 2)
        self.assertEqual(result.tool_call_count, 1)
        self.assertEqual(len(result.trace), 3)
        self.assertEqual(result.trace[1].kind, "tool_observation")
        self.assertEqual(result.trace[1].observation.output, {"text": "hello"})

    async def test_stops_when_max_steps_is_exceeded_without_final_answer(self) -> None:
        class LoopModel:
            async def decide_next_action(self, context: ModelContextView) -> AgentAction:
                return ToolCallAction(
                    call_id="loop-call",
                    tool_name="loop",
                    input={},
                )

        class LoopExecutor:
            async def execute_tool_call(
                self,
                action: ToolCallAction,
                context: ExecutionContext,
            ) -> ToolObservation:
                return ToolObservation(
                    call_id=action.call_id,
                    tool_name=action.tool_name,
                    ok=True,
                    output={},
                )

        result = await run_agent_loop(
            RunAgentLoopInput(
                model=LoopModel(),
                executor=LoopExecutor(),
                user_input="hello",
                max_steps=2,
            )
        )

        self.assertEqual(result.status, "max_steps_exceeded")
        self.assertIsNone(result.answer)
        self.assertEqual(result.steps, 2)
        self.assertEqual(result.model_call_count, 2)
        self.assertEqual(result.tool_call_count, 2)
        self.assertEqual(len(result.trace), 4)

    async def test_passes_snapshot_model_view_and_execution_context(self) -> None:
        model_contexts: list[ModelContextView] = []
        execution_contexts: list[ExecutionContext] = []

        class SnapshotModel:
            def __init__(self) -> None:
                self.calls = 0

            async def decide_next_action(self, context: ModelContextView) -> AgentAction:
                model_contexts.append(context)
                self.calls += 1
                if self.calls == 1:
                    return ToolCallAction(
                        call_id="call-1",
                        tool_name="echo",
                        input={"text": context.user_input},
                    )

                return FinalAnswerAction(answer="done")

        class SnapshotExecutor:
            async def execute_tool_call(
                self,
                action: ToolCallAction,
                context: ExecutionContext,
            ) -> ToolObservation:
                execution_contexts.append(context)
                return ToolObservation(
                    call_id=action.call_id,
                    tool_name=action.tool_name,
                    ok=True,
                    output=action.input,
                )

        result = await run_agent_loop(
            RunAgentLoopInput(
                session_id="session-1",
                trace_id="trace-1",
                user_id="user-1",
                permissions=("orders:read",),
                metadata={"source": "test"},
                model=SnapshotModel(),
                executor=SnapshotExecutor(),
                user_input="hello",
                max_steps=3,
            )
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(model_contexts), 2)
        self.assertEqual(model_contexts[0].session_id, "session-1")
        self.assertEqual(model_contexts[0].current_step, 0)
        self.assertEqual(model_contexts[0].model_call_count, 0)
        self.assertEqual(model_contexts[0].tool_call_count, 0)
        self.assertEqual(model_contexts[0].messages[0].content, "hello")
        self.assertEqual(model_contexts[0].recent_events, ())
        self.assertEqual(model_contexts[0].permissions, ("orders:read",))
        self.assertIsInstance(model_contexts[0].metadata, types.MappingProxyType)
        self.assertEqual(dict(model_contexts[0].metadata or {}), {"source": "test"})
        self.assertEqual(model_contexts[1].recent_events, result.trace[:2])

        self.assertEqual(len(execution_contexts), 1)
        self.assertEqual(execution_contexts[0].session_id, "session-1")
        self.assertEqual(execution_contexts[0].current_step, 0)
        self.assertEqual(execution_contexts[0].trace_id, "trace-1")
        self.assertEqual(execution_contexts[0].user_id, "user-1")
        self.assertEqual(execution_contexts[0].permissions, ("orders:read",))
        self.assertIsInstance(execution_contexts[0].metadata, types.MappingProxyType)

    async def test_returns_ask_user_without_invoking_a_tool(self) -> None:
        result = await run_demo("Where is my package?")

        self.assertEqual(result.status, "needs_user_input")
        self.assertIsNone(result.answer)
        self.assertEqual(
            result.question,
            "Please share your order number in the format ORD-1234 so I can check the status.",
        )
        self.assertIsNone(result.handoff_reason)
        self.assertEqual(result.steps, 1)
        self.assertEqual(result.model_call_count, 1)
        self.assertEqual(result.tool_call_count, 0)

    async def test_returns_handoff_without_invoking_a_tool_for_risky_requests(self) -> None:
        result = await run_demo(
            "I need a chargeback for order ORD-1001 and my lawyer is involved"
        )

        self.assertEqual(result.status, "handoff_requested")
        self.assertIsNone(result.answer)
        self.assertIsNone(result.question)
        self.assertEqual(
            result.handoff_reason,
            "This request has fraud or legal risk and should be reviewed by a human agent.",
        )
        self.assertEqual(result.steps, 1)
        self.assertEqual(result.model_call_count, 1)
        self.assertEqual(result.tool_call_count, 0)

    async def test_demo_model_and_executor_complete_a_full_customer_service_loop(self) -> None:
        result = await run_demo("Where is order ORD-1001?")

        self.assertEqual(result.status, "completed")
        self.assertEqual(
            result.answer,
            "Your order ORD-1001 has shipped and is expected to arrive by 2026-04-18.",
        )
        self.assertEqual(result.steps, 3)
        self.assertEqual(result.model_call_count, 3)
        self.assertEqual(result.tool_call_count, 2)


class RuntimeConfigTests(unittest.TestCase):
    def test_runtime_model_config_defaults_to_demo_mode(self) -> None:
        config = read_runtime_model_config({})
        self.assertEqual(config, DemoRuntimeModelConfig())

    def test_runtime_model_config_empty_env_does_not_read_process_env(self) -> None:
        with patch.dict(os.environ, {"AGENT_MODEL_MODE": "dev"}, clear=True):
            config = read_runtime_model_config({})

        self.assertEqual(config, DemoRuntimeModelConfig())

    def test_runtime_model_config_rejects_dev_mode_without_model_id(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "AGENT_MODEL_MODE=dev requires AGENT_MODEL_ID to be set.",
        ):
            read_runtime_model_config(
                {
                    "AGENT_MODEL_MODE": "dev",
                    "OPENAI_API_KEY": "test-key",
                }
            )

    def test_runtime_model_config_rejects_unsupported_providers(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported AGENT_MODEL_ID provider: bedrock.",
        ):
            read_runtime_model_config(
                {
                    "AGENT_MODEL_MODE": "dev",
                    "AGENT_MODEL_ID": "bedrock:claude-sonnet",
                }
            )

    def test_runtime_model_config_requires_the_matching_provider_api_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "ANTHROPIC_API_KEY must be set."):
            read_runtime_model_config(
                {
                    "AGENT_MODEL_MODE": "dev",
                    "AGENT_MODEL_ID": "anthropic:claude-sonnet-4-5",
                }
            )

    def test_runtime_model_config_reads_a_generic_base_url_override(self) -> None:
        config = read_runtime_model_config(
            {
                "AGENT_MODEL_MODE": "dev",
                "AGENT_MODEL_ID": "openai:gpt-4.1",
                "OPENAI_API_KEY": "test-openai-key",
                "AGENT_MODEL_BASE_URL": "https://proxy.example.com/v1",
            }
        )

        self.assertEqual(
            config,
            DevRuntimeModelConfig(
                model_id="openai:gpt-4.1",
                provider="openai",
                model_name="gpt-4.1",
                api_key="test-openai-key",
                base_url="https://proxy.example.com/v1",
            ),
        )

    def test_create_runtime_model_uses_demo_model_in_demo_mode(self) -> None:
        model = create_runtime_model({"AGENT_MODEL_MODE": "demo"})
        self.assertIsInstance(model, DemoModel)

    def test_create_runtime_model_marks_dev_mode_as_future_phase(self) -> None:
        with self.assertRaisesRegex(NotImplementedError, "Phase 2"):
            create_runtime_model(
                {
                    "AGENT_MODEL_MODE": "dev",
                    "AGENT_MODEL_ID": "openai:gpt-4.1",
                    "OPENAI_API_KEY": "test-openai-key",
                }
            )


if __name__ == "__main__":
    unittest.main()
