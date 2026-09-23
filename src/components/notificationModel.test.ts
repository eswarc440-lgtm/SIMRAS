import { describe, expect, it } from "vitest";
import { filterNotifications, markNotificationRead, unreadCount } from "./notificationModel";

const notifications = [
  { id: "N1", type: "RISK_CHANGED", read_at: null, category: "RISK" },
  { id: "N2", type: "INSPECTION_DUE", read_at: "2026-09-23", category: "INSPECTION" },
] as any[];

describe("notification state", () => {
  it("filters unread and workflow categories", () => {
    expect(filterNotifications(notifications, "unread").map((item) => item.id)).toEqual(["N1"]);
    expect(filterNotifications(notifications, "inspections").map((item) => item.id)).toEqual(["N2"]);
  });
  it("marks read without mutating the original list", () => {
    const next = markNotificationRead(notifications, "N1", "2026-09-23T08:00:00Z");
    expect(unreadCount(next)).toBe(0);
    expect(notifications[0].read_at).toBeNull();
  });
});
