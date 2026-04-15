export const ORDER_STATUS_VALUES = ["processing", "shipped", "delayed", "not_found"] as const;

type DemoToolCatalogItem = {
  name: string;
  description: string;
  whenToUse: string;
  inputShape: Record<string, string>;
  outputShape: Record<string, string>;
};

export const DEMO_TOOL_CATALOG: readonly DemoToolCatalogItem[] = [
  {
    name: "lookupOrder",
    description: "Look up the latest order fulfillment status.",
    whenToUse: "Use when the user has provided an order number and no order lookup result exists yet.",
    inputShape: {
      orderId: "A non-empty string like ORD-1001.",
    },
    outputShape: {
      orderId: "The normalized order number.",
      status: `One of: ${ORDER_STATUS_VALUES.join(", ")}.`,
      estimatedDelivery: "A date string like 2026-04-18 or null when unavailable.",
    },
  },
  {
    name: "draftReply",
    description: "Draft a customer support reply based on the order status.",
    whenToUse: "Use only after a successful lookupOrder result exists and before returning final_answer.",
    inputShape: {
      orderId: "The order number that was looked up.",
      status: `One of: ${ORDER_STATUS_VALUES.join(", ")}.`,
      estimatedDelivery: "A date string or null.",
    },
    outputShape: {
      draft: "A natural-language reply for the customer.",
    },
  },
] as const;

export function formatDemoToolCatalog(): string {
  return DEMO_TOOL_CATALOG.map((tool) => {
    const inputLines = Object.entries(tool.inputShape)
      .map(([key, value]) => `    - ${key}: ${value}`)
      .join("\n");
    const outputLines = Object.entries(tool.outputShape)
      .map(([key, value]) => `    - ${key}: ${value}`)
      .join("\n");

    return [
      `- ${tool.name}: ${tool.description}`,
      `  When to use: ${tool.whenToUse}`,
      "  Input:",
      inputLines,
      "  Output:",
      outputLines,
    ].join("\n");
  }).join("\n");
}
