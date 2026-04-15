import assert from "node:assert/strict";
import test from "node:test";

import { runAgentLoop } from "../../src/agent/agent-loop.js";
import type {
  ExecutionContext,
  ModelContextView,
  ToolCallAction,
  ToolObservation,
} from "../../src/agent/types.js";
import { runDemo } from "../../src/demo/run-demo.js";

test("completes immediately when model returns final_answer", async () => {
  const result = await runAgentLoop({
    model: {
      decideNextAction: async () => ({
        type: "final_answer",
        answer: "done",
      }),
    },
    executor: {
      executeToolCall: async () => {
        throw new Error("should not be called");
      },
    },
    userInput: "hello",
    maxSteps: 3,
  });

  assert.equal(result.status, "completed");
  assert.equal(result.answer, "done");
  assert.equal(result.question, null);
  assert.equal(result.handoffReason, null);
  assert.equal(result.steps, 1);
  assert.equal(result.modelCallCount, 1);
  assert.equal(result.toolCallCount, 0);
  assert.deepEqual(result.trace, [
    {
      kind: "model_decision",
      action: {
        type: "final_answer",
        answer: "done",
      },
    },
  ]);
});

test("executes tool_call then completes with final_answer", async () => {
  let calls = 0;

  const result = await runAgentLoop({
    model: {
      decideNextAction: async () => {
        calls += 1;

        if (calls === 1) {
          return {
            type: "tool_call",
            callId: "call-1",
            toolName: "echo",
            input: { text: "hello" },
          };
        }

        return {
          type: "final_answer",
          answer: "done after tool",
        };
      },
    },
    executor: {
      executeToolCall: async (action): Promise<ToolObservation> => ({
        kind: "tool_result",
        callId: action.callId,
        toolName: action.toolName,
        ok: true,
        output: action.input,
      }),
    },
    userInput: "hello",
    maxSteps: 3,
  });

  assert.equal(result.status, "completed");
  assert.equal(result.answer, "done after tool");
  assert.equal(result.steps, 2);
  assert.equal(result.modelCallCount, 2);
  assert.equal(result.toolCallCount, 1);
  assert.equal(result.trace.length, 3);
  assert.deepEqual(result.trace[1], {
    kind: "tool_observation",
    action: {
      type: "tool_call",
      callId: "call-1",
      toolName: "echo",
      input: { text: "hello" },
    },
    observation: {
      kind: "tool_result",
      callId: "call-1",
      toolName: "echo",
      ok: true,
      output: { text: "hello" },
    },
  });
});

test("stops when maxSteps is exceeded without final_answer", async () => {
  const result = await runAgentLoop({
    model: {
      decideNextAction: async () => ({
        type: "tool_call",
        callId: "loop-call",
        toolName: "loop",
        input: {},
      }),
    },
    executor: {
      executeToolCall: async (action): Promise<ToolObservation> => ({
        kind: "tool_result",
        callId: action.callId,
        toolName: action.toolName,
        ok: true,
        output: {},
      }),
    },
    userInput: "hello",
    maxSteps: 2,
  });

  assert.equal(result.status, "max_steps_exceeded");
  assert.equal(result.answer, null);
  assert.equal(result.steps, 2);
  assert.equal(result.modelCallCount, 2);
  assert.equal(result.toolCallCount, 2);
  assert.equal(result.trace.length, 4);
});

test("passes a readonly model view snapshot and readonly execution context", async () => {
  const modelContexts: ModelContextView[] = [];
  const executionContexts: ExecutionContext[] = [];
  let calls = 0;

  const result = await runAgentLoop({
    sessionId: "session-1",
    traceId: "trace-1",
    userId: "user-1",
    permissions: ["orders:read"],
    metadata: { source: "test" },
    model: {
      decideNextAction: async (context) => {
        modelContexts.push(context);
        calls += 1;

        if (calls === 1) {
          return {
            type: "tool_call",
            callId: "call-1",
            toolName: "echo",
            input: { text: context.userInput },
          };
        }

        return {
          type: "final_answer",
          answer: "done",
        };
      },
    },
    executor: {
      executeToolCall: async (
        action: ToolCallAction,
        context: ExecutionContext,
      ): Promise<ToolObservation> => {
        executionContexts.push(context);

        return {
          kind: "tool_result",
          callId: action.callId,
          toolName: action.toolName,
          ok: true,
          output: action.input,
        };
      },
    },
    userInput: "hello",
    maxSteps: 3,
  });

  assert.equal(result.status, "completed");
  assert.equal(modelContexts.length, 2);
  assert.equal(modelContexts[0]?.sessionId, "session-1");
  assert.equal(modelContexts[0]?.currentStep, 0);
  assert.equal(modelContexts[0]?.modelCallCount, 0);
  assert.equal(modelContexts[0]?.toolCallCount, 0);
  assert.deepEqual(modelContexts[0]?.messages, [
    {
      role: "user",
      content: "hello",
    },
  ]);
  assert.deepEqual(modelContexts[0]?.recentEvents, []);
  assert.deepEqual(modelContexts[0]?.permissions, ["orders:read"]);
  assert.deepEqual(modelContexts[0]?.metadata, { source: "test" });
  assert(modelContexts[0] ? Object.isFrozen(modelContexts[0].messages) : false);
  assert(modelContexts[0] ? Object.isFrozen(modelContexts[0].permissions) : false);
  assert.deepEqual(modelContexts[1]?.recentEvents, result.trace.slice(0, 2));
  assert(modelContexts[1]?.recentEvents !== result.trace);

  assert.equal(executionContexts.length, 1);
  assert.deepEqual(executionContexts[0], {
    sessionId: "session-1",
    currentStep: 0,
    traceId: "trace-1",
    userId: "user-1",
    permissions: ["orders:read"],
    metadata: { source: "test" },
  });
  assert(executionContexts[0] ? Object.isFrozen(executionContexts[0].permissions) : false);
});

test("returns ask_user without invoking a tool when required input is missing", async () => {
  const result = await runDemo("Where is my package?");

  assert.equal(result.status, "needs_user_input");
  assert.equal(result.answer, null);
  assert.equal(
    result.question,
    "Please share your order number in the format ORD-1234 so I can check the status.",
  );
  assert.equal(result.handoffReason, null);
  assert.equal(result.steps, 1);
  assert.equal(result.modelCallCount, 1);
  assert.equal(result.toolCallCount, 0);
});

test("returns handoff_to_human without invoking a tool for risky requests", async () => {
  const result = await runDemo("I need a chargeback for order ORD-1001 and my lawyer is involved");

  assert.equal(result.status, "handoff_requested");
  assert.equal(result.answer, null);
  assert.equal(result.question, null);
  assert.equal(
    result.handoffReason,
    "This request has fraud or legal risk and should be reviewed by a human agent.",
  );
  assert.equal(result.steps, 1);
  assert.equal(result.modelCallCount, 1);
  assert.equal(result.toolCallCount, 0);
});

test("demo model and executor complete a full customer-service loop", async () => {
  const result = await runDemo("Where is order ORD-1001?");

  assert.equal(result.status, "completed");
  assert.equal(
    result.answer,
    "Your order ORD-1001 has shipped and is expected to arrive by 2026-04-18.",
  );
  assert.equal(result.steps, 3);
  assert.equal(result.modelCallCount, 3);
  assert.equal(result.toolCallCount, 2);
  assert.equal(result.trace.length, 5);
  assert.deepEqual(result.trace[1], {
    kind: "tool_observation",
    action: {
      type: "tool_call",
      callId: "call-1-lookup-order",
      toolName: "lookupOrder",
      input: {
        orderId: "ORD-1001",
      },
    },
    observation: {
      kind: "tool_result",
      callId: "call-1-lookup-order",
      toolName: "lookupOrder",
      ok: true,
      output: {
        orderId: "ORD-1001",
        status: "shipped",
        estimatedDelivery: "2026-04-18",
      },
    },
  });
});
