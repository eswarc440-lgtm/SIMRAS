import { describe, expect, it } from "vitest";
import { groupSearchResults, moveSearchIndex, shouldSearch } from "./searchModel";

const results = [
  { type: "maintenance", id: "WO-1", title: "Gate service", subtitle: "Prakasam", action_url: "/maintenance" },
  { type: "asset", id: "AP_DAM_00001", title: "Prakasam Barrage", subtitle: "NTR", action_url: "/digital-twin" },
  { type: "inspection", id: "INSP-1", title: "INSP-1", subtitle: "Prakasam", action_url: "/inspections" },
] as any;

describe("global search model", () => {
  it("requires at least two non-space characters", () => {
    expect(shouldSearch(" a ")).toBe(false);
    expect(shouldSearch(" ap ")).toBe(true);
  });

  it("groups structured results without losing order within groups", () => {
    const grouped = groupSearchResults(results);
    expect(grouped.assets.map((item) => item.id)).toEqual(["AP_DAM_00001"]);
    expect(grouped.inspections.map((item) => item.id)).toEqual(["INSP-1"]);
    expect(grouped.maintenance.map((item) => item.id)).toEqual(["WO-1"]);
  });

  it("wraps keyboard selection safely", () => {
    expect(moveSearchIndex(-1, 1, 3)).toBe(0);
    expect(moveSearchIndex(2, 1, 3)).toBe(0);
    expect(moveSearchIndex(0, -1, 3)).toBe(2);
    expect(moveSearchIndex(0, 1, 0)).toBe(-1);
  });
});
