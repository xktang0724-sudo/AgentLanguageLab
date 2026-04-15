declare module "node:assert/strict" {
  type AssertFn = (value: unknown, message?: string) => asserts value;

  interface AssertModule extends AssertFn {
    equal(actual: unknown, expected: unknown, message?: string): void;
    deepEqual(actual: unknown, expected: unknown, message?: string): void;
  }

  const assert: AssertModule;
  export default assert;
}

declare module "node:test" {
  export interface TestContext {}

  export default function test(
    name: string,
    fn: (context: TestContext) => void | Promise<void>,
  ): void;
}

declare const process: {
  env: Record<string, string | undefined>;
};
