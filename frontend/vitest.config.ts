import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["lib/**/*.test.ts", "tests/**/*.test.ts"],
    // The JUnit report carries each test's spec tag in its name, so the coverage check and
    // the build walkthrough can join frontend tests to requirements (decision record 0012).
    reporters: ["default", ["junit", { outputFile: "test-results/junit.xml" }]],
  },
});
