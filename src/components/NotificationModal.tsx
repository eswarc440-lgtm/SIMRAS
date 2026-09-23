import React, { useEffect, useState } from "react";
import { X, Bell, CheckCircle2, AlertTriangle, Info, Check } from "lucide-react";
import { filterNotifications, markNotificationRead, unreadCount, type NotificationFilter } from "./notificationModel";

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  category: "ALERT" | "INSPECTION" | "MAINTENANCE" | "REVIEW";
  asset_code?: string;
  read: boolean;
  timestamp: string;
  read_at?: string | null;
}

interface NotificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectAsset?: (assetCode: string) => void;
  onUnreadChange?: (count: number) => void;
}

export function NotificationModal({ isOpen, onClose, onSelectAsset, onUnreadChange }: NotificationModalProps) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<NotificationFilter>("unread");
  const authHeaders = () => { const token = localStorage.getItem("simras_token"); return token ? { Authorization: `Bearer ${token}` } : {}; };

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/notifications", { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
        onUnreadChange?.(unreadCount(data));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen]);

  const markAsRead = async (id: string) => {
    try {
      await fetch(`/api/v1/notifications/${id}/read`, { method: "POST", headers: authHeaders() });
      setNotifications((prev) => { const next = markNotificationRead(prev, id); onUnreadChange?.(unreadCount(next)); return next; });
    } catch (e) {
      console.error(e);
    }
  };

  const markAllAsRead = async () => {
    try {
      await fetch("/api/v1/notifications/read-all", { method: "POST", headers: authHeaders() });
      setNotifications((prev) => { const next = prev.map((n) => ({ ...n, read: true, read_at: new Date().toISOString() })); onUnreadChange?.(0); return next; });
    } catch (e) {
      console.error(e);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
      <div className="bg-white border border-[#D9E3EC] rounded-xl max-w-lg w-full p-6 shadow-2xl relative text-[#172B3A] flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between pb-4 border-b border-[#D9E3EC]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-[#0875BE]">
              <Bell className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#0C4775] tracking-tight">System Alerts & Notifications</h2>
              <p className="text-[11px] text-[#61788A]">Real-time operational alerts for Andhra Pradesh infrastructure</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={markAllAsRead}
              className="text-xs text-[#0875BE] hover:text-[#0C4775] font-semibold flex items-center gap-1 transition px-2.5 py-1 rounded bg-[#EBF5FB] border border-[#D9E3EC]"
            >
              <Check className="w-3.5 h-3.5" />
              Mark all read
            </button>
            <button
              onClick={onClose}
              className="text-[#61788A] hover:text-[#172B3A] transition p-1 rounded hover:bg-slate-100"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex gap-1 overflow-x-auto py-2">{(["unread", "all", "risk", "inspections", "maintenance", "assets", "reviews"] as NotificationFilter[]).map((value) => <button key={value} onClick={() => setFilter(value)} className={`rounded px-2 py-1 text-[10px] font-bold capitalize ${filter === value ? "bg-[#0875BE] text-white" : "bg-slate-100 text-slate-600"}`}>{value}</button>)}</div>
        <div className="overflow-y-auto divide-y divide-slate-100 py-2 flex-1 space-y-2 pr-1 mt-2">
          {loading ? (
            <div className="text-center py-8 text-sm text-[#61788A]">Loading alerts...</div>
          ) : filterNotifications(notifications, filter).length === 0 ? (
            <div className="text-center py-8 text-sm text-[#61788A]">No active alerts at this time.</div>
          ) : (
            filterNotifications(notifications, filter).map((item) => (
              <div
                key={item.id}
                className={`p-3 rounded-lg border transition ${
                  item.read
                    ? "bg-[#F5F8FB] border-[#D9E3EC] opacity-80"
                    : "bg-white border-blue-200 shadow-xs"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 shrink-0">
                    {item.severity === "CRITICAL" ? (
                      <AlertTriangle className="w-4 h-4 text-[#D94343]" />
                    ) : item.severity === "WARNING" ? (
                      <AlertTriangle className="w-4 h-4 text-[#F2A623]" />
                    ) : (
                      <Info className="w-4 h-4 text-[#0875BE]" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="text-xs font-bold text-[#172B3A] truncate">{item.title}</h4>
                      <span className="text-[10px] text-[#61788A] shrink-0">
                        {new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                    <p className="text-xs text-[#61788A] mt-1 line-clamp-2 leading-relaxed">{item.message}</p>

                    <div className="flex items-center justify-between mt-2 pt-1">
                      {item.asset_code && onSelectAsset ? (
                        <button
                          onClick={() => {
                            onSelectAsset(item.asset_code!);
                            onClose();
                          }}
                          className="text-[11px] text-[#0875BE] hover:underline font-mono font-bold"
                        >
                          View {item.asset_code} →
                        </button>
                      ) : (
                        <span />
                      )}

                      {!item.read && (
                        <button
                          onClick={() => markAsRead(item.id)}
                          className="text-[10px] text-[#61788A] hover:text-[#172B3A] transition font-medium"
                        >
                          Mark as read
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
