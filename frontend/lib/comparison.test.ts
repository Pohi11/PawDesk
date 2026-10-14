import { expect } from "vitest";

import { specTest } from "../tests/spec";
import { type ArchitectureHeadline, comparisonRows, numeric } from "./comparison";

const base: ArchitectureHeadline = {
  cases: 20,
  decision_accuracy: "18/20",
  unsafe_confirmations: 0,
  missed_confirmations: 2,
  injections_to_person: "3/3",
  errors: 0,
  total_cost_usd: "0.04",
  average_cost_usd: "0.002",
  average_seconds: 9.5,
  median_seconds: 8.1,
  average_model_calls: 4,
};

specTest(
  "architecture-comparison",
  "Both architectures are scored the same way",
  "the dashboard marks the better side of each metric the same way for both",
  () => {
    const rows = comparisonRows({
      hybrid: base,
      autonomous: {
        ...base,
        decision_accuracy: "15/20",
        unsafe_confirmations: 2,
        injections_to_person: "1/3",
        average_cost_usd: "0.006",
        average_seconds: 7.0,
      },
    });
    const better = Object.fromEntries(rows.map((r) => [r.label, r.better]));

    expect(better["Decision accuracy"]).toBe("hybrid");
    expect(better["Unsafe confirmations"]).toBe("hybrid");
    expect(better["Injections handed to a person"]).toBe("hybrid");
    expect(better["Average cost per case"]).toBe("hybrid");
    expect(better["Average latency"]).toBe("autonomous");
    expect(better["Errors"]).toBeNull(); // a tie favors neither
    expect(rows.find((r) => r.label === "Average cost per case")?.autonomous).toBe("$0.006000");
  },
);

specTest("architecture-comparison", "Both architectures are scored the same way", "fractions compare by value", () => {
  expect(numeric("33/36")).toBeCloseTo(0.9167, 4);
  expect(numeric("0/0")).toBeNull();
  expect(numeric("0.0012")).toBe(0.0012);
  expect(numeric(null)).toBeNull();
});
