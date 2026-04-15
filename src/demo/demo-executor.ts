import { ToolRegistry } from "../agent/action-executor.js";
import type { ToolDefinition } from "../agent/types.js";

type LookupOrderInput = {
  orderId: string;
};

type LookupOrderOutput = {
  orderId: string;
  status: "processing" | "shipped" | "delayed" | "not_found";
  estimatedDelivery: string | null;
};

type DraftReplyInput = {
  orderId: string;
  status: LookupOrderOutput["status"];
  estimatedDelivery: string | null;
};

type DraftReplyOutput = {
  draft: string;
};

const ORDER_FIXTURES: Record<string, LookupOrderOutput> = {
  "ORD-1001": {
    orderId: "ORD-1001",
    status: "shipped",
    estimatedDelivery: "2026-04-18",
  },
  "ORD-1002": {
    orderId: "ORD-1002",
    status: "processing",
    estimatedDelivery: "2026-04-20",
  },
  "ORD-4040": {
    orderId: "ORD-4040",
    status: "delayed",
    estimatedDelivery: "2026-04-22",
  },
};

const lookupOrderTool: ToolDefinition<LookupOrderInput, LookupOrderOutput, "lookupOrder"> = {
  name: "lookupOrder",
  description: "Look up the latest order fulfillment status.",
  validate(input: unknown): LookupOrderInput {
    const value = asRecord(input);
    return {
      orderId: readRequiredString(value, "orderId"),
    };
  },
  async execute(input, context): Promise<LookupOrderOutput> {
    if (!context.permissions.includes("orders:read")) {
      throw new Error("Missing permission: orders:read");
    }

    return ORDER_FIXTURES[input.orderId] ?? {
      orderId: input.orderId,
      status: "not_found",
      estimatedDelivery: null,
    };
  },
};

const draftReplyTool: ToolDefinition<DraftReplyInput, DraftReplyOutput, "draftReply"> = {
  name: "draftReply",
  description: "Draft a customer support reply based on the order status.",
  validate(input: unknown): DraftReplyInput {
    const value = asRecord(input);
    const estimatedDelivery = value.estimatedDelivery;

    if (estimatedDelivery !== null && estimatedDelivery !== undefined && typeof estimatedDelivery !== "string") {
      throw new Error("estimatedDelivery must be a string or null");
    }

    const status = readRequiredString(value, "status");
    if (!["processing", "shipped", "delayed", "not_found"].includes(status)) {
      throw new Error(`Unsupported order status: ${status}`);
    }

    return {
      orderId: readRequiredString(value, "orderId"),
      status: status as DraftReplyInput["status"],
      estimatedDelivery: estimatedDelivery ?? null,
    };
  },
  async execute(input): Promise<DraftReplyOutput> {
    const draft = createDraftReply(input);
    return { draft };
  },
};

export class DemoExecutor extends ToolRegistry {
  constructor() {
    super(
      new Map<string, ToolDefinition<unknown, unknown>>([
        [lookupOrderTool.name, lookupOrderTool],
        [draftReplyTool.name, draftReplyTool],
      ]),
    );
  }
}

function createDraftReply(input: DraftReplyInput): string {
  if (input.status === "not_found") {
    return `I couldn't find order ${input.orderId}. Please confirm the order number so I can check again.`;
  }

  if (input.status === "processing") {
    return `Your order ${input.orderId} is still processing. The current estimated delivery date is ${input.estimatedDelivery}.`;
  }

  if (input.status === "shipped") {
    return `Your order ${input.orderId} has shipped and is expected to arrive by ${input.estimatedDelivery}.`;
  }

  return `Your order ${input.orderId} is delayed. The latest estimated delivery date is ${input.estimatedDelivery}.`;
}

function asRecord(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Tool input must be an object");
  }

  return value as Record<string, unknown>;
}

function readRequiredString(value: Record<string, unknown>, key: string): string {
  const field = value[key];

  if (typeof field !== "string" || field.length === 0) {
    throw new Error(`${key} must be a non-empty string`);
  }

  return field;
}
