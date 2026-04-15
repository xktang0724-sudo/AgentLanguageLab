import assert from "node:assert/strict";
import test from "node:test";

import { runAgentLoop } from "../../src/agent/agent-loop.js";
import type { ExecutionContext, ModelContextView } from "../../src/agent/types.js";
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
      executeBuiltinCall: async () => {
        throw new Error("should not be called");
      },
    },
    userInput: "hello",
    maxSteps: 3,
  });

  assert.equal(result.status, "completed");
  assert.equal(result.answer, "done");
  assert.equal(result.steps, 0);
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

test("executes builtin_call then completes with final_answer", async () => {
  let calls = 0;

  const result = await runAgentLoop({
    model: {
      decideNextAction: async () => {
        calls += 1;

        if (calls === 1) {
          return {
            type: "builtin_call",
            name: "echo",
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
      executeBuiltinCall: async (action) => ({
        ok: true,
        output: action.input,
      }),
    },
    userInput: "hello",
    maxSteps: 3,
  });

  assert.equal(result.status, "completed");
  assert.equal(result.answer, "done after tool");
  assert.equal(result.steps, 1);
  assert.equal(result.trace.length, 3);
  assert.deepEqual(result.trace[1], {
    kind: "action_result",
    action: {
      type: "builtin_call",
      name: "echo",
      input: { text: "hello" },
    },
    result: {
      ok: true,
      output: { text: "hello" },
    },
  });
});

test("stops when maxSteps is exceeded without final_answer", async () => {
  const result = await runAgentLoop({
    model: {
      decideNextAction: async () => ({
        type: "builtin_call",
        name: "loop",
        input: {},
      }),
    },
    executor: {
      executeBuiltinCall: async () => ({
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
  assert.equal(result.trace.length, 4);
});

test("passes a readonly model view snapshot and minimal execution context", async () => {
  const modelContexts: ModelContextView[] = [];
  const executionContexts: ExecutionContext[] = [];
  let calls = 0;

  const result = await runAgentLoop({
    sessionId: "session-1",
    metadata: { source: "test" },
    model: {
      decideNextAction: async (context) => {
        modelContexts.push(context);
        calls += 1;

        if (calls === 1) {
          return {
            type: "builtin_call",
            name: "echo",
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
      executeBuiltinCall: async (action, context) => {
        executionContexts.push(context);

        return {
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
  assert.deepEqual(modelContexts[0]?.messages, [
    {
      role: "user",
      content: "hello",
    },
  ]);
  assert.deepEqual(modelContexts[0]?.recentEvents, []);
  assert.deepEqual(modelContexts[1]?.recentEvents, result.trace.slice(0, 2));
  assert(modelContexts[1]?.recentEvents !== result.trace);
  assert.deepEqual(modelContexts[0]?.metadata, { source: "test" });

  assert.equal(executionContexts.length, 1);
  assert.deepEqual(executionContexts[0], {
    sessionId: "session-1",
    currentStep: 0,
    metadata: { source: "test" },
  });
});

test("demo model and executor complete a full loop", async () => {
  const result = await runDemo("hello");

  assert.equal(result.status, "completed");
  assert.equal(result.answer, "Done: hello");
  assert.equal(result.steps, 1);
  assert.equal(result.trace.length, 3);
});
