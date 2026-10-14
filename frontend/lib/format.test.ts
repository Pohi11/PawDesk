import { expect, test } from "vitest";

import { formatService, formatStay } from "./format";

test("stays read the way the desk says them", () => {
  expect(formatStay("2027-03-10", "2027-03-13")).toBe("Mar 10–13, 2027");
  expect(formatStay("2027-03-31", "2027-04-02")).toBe("Mar 31 – Apr 2, 2027");
  expect(formatStay("2027-03-15", "2027-03-15")).toBe("Mar 15, 2027");
  expect(formatStay("2027-12-30", "2028-01-02")).toBe("Dec 30, 2027 – Jan 2, 2028");
  expect(formatStay(null, null)).toBe("Dates unclear");
});

test("services are capitalized", () => {
  expect(formatService("boarding")).toBe("Boarding");
  expect(formatService(null)).toBe("Service unclear");
});
