import { describe, expect, it } from "vitest";
import { riskColor } from "./utils";

describe("riskColor", () => {
  it("uses the critical colour for high risk", () => {
    expect(riskColor("HIGH")).toBe("#ff5b62");
  });
});

