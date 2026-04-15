export type FinalAnswerAction = {
  type: "final_answer";
  answer: string;
};

export type BuiltinCallAction = {
  type: "builtin_call";
  name: string;
  input: unknown;
};

export type AgentAction = FinalAnswerAction | BuiltinCallAction;

export type BuiltinResult = {
  ok: boolean;
  output: unknown;
};

export type Message = {
  role: "user" | "assistant" | "tool";
  content: unknown;
};

export type AgentTraceItem =
  | {
      kind: "model_decision";
      action: AgentAction;
    }
  | {
      kind: "action_result";
      action: BuiltinCallAction;
      result: BuiltinResult;
    };

export type AgentSessionStatus =
  | "running"
  | "completed"
  | "failed"
  | "max_steps_exceeded";

export type AgentSessionState = {
  sessionId: string;
  userInput: string;
  currentStep: number;
  status: AgentSessionStatus;
  messages: Message[];
  trace: AgentTraceItem[];
  metadata?: Record<string, unknown>;
};

export type ModelContextView = {
  sessionId: string;
  userInput: string;
  currentStep: number;
  recentEvents: readonly AgentTraceItem[];
  messages: readonly Message[];
  metadata?: Readonly<Record<string, unknown>>;
};

export type ExecutionContext = {
  sessionId: string;
  currentStep: number;
  metadata?: Readonly<Record<string, unknown>>;
};

export type AgentRunResult = {
  status: "completed" | "max_steps_exceeded";
  answer: string | null;
  steps: number;
  trace: AgentTraceItem[];
};
