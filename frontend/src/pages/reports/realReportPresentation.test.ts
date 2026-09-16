import { describe, expect, it } from "vitest";
import { displayableReportEntries } from "./realReportPresentation";

describe("displayableReportEntries", () => {
  it("omits unavailable and insufficient placeholders", () => {
    const rows = displayableReportEntries({
      length_m: 1232.92,
      risk: "INSUFFICIENT_DATA",
      width: "Not available",
      owner: "Government of Andhra Pradesh",
      zero: 0,
    });
    expect(rows).toEqual([
      ["Length M", "1232.92"],
      ["Owner", "Government of Andhra Pradesh"],
      ["Zero", "0"],
    ]);
  });
});
