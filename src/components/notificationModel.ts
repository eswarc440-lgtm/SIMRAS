export type NotificationFilter = "all" | "unread" | "risk" | "inspections" | "maintenance" | "assets" | "reviews";
export interface NotificationState { id: string; type?: string; category?: string; read?: boolean; read_at?: string | null }
export function unreadCount<T extends NotificationState>(items: readonly T[]) { return items.filter((item) => !(item.read_at || item.read)).length; }
export function markNotificationRead<T extends NotificationState>(items: readonly T[], id: string, readAt = new Date().toISOString()): T[] { return items.map((item) => item.id === id ? { ...item, read: true, read_at: readAt } : item) as T[]; }
export function filterNotifications<T extends NotificationState>(items: readonly T[], filter: NotificationFilter): T[] {
  if (filter === "all") return [...items];
  if (filter === "unread") return items.filter((item) => !(item.read_at || item.read));
  const category = filter === "risk" ? "RISK" : filter === "inspections" ? "INSPECTION" : filter === "maintenance" ? "MAINTENANCE" : filter === "assets" ? "ASSET" : "REVIEW";
  return items.filter((item) => String(item.category ?? item.type ?? "").toUpperCase().includes(category));
}
