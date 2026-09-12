import { useEffect, useState } from "react";
import { AlertTriangle, Bell, Info } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { PageHeader } from "../../components/common/PageHeader";
import { apiRequest } from "../../services/api";

type RiskItem = {
  id?: string | number;
  asset_id?: string;
  asset_name?: string;
  risk_score?: number | null;
  risk_level?: string | null;
  confidence_score?: number | null;
  prediction_time?: string | null;
};

type Notification = {
  id: string;
  title: string;
  body: string;
  severity: "critical" | "warning" | "info";
  time: string;
};

const severityMap = {
  critical: { icon: AlertTriangle, cls: "border-danger/30 bg-danger/10 text-danger", label: "Critical" },
  warning: { icon: Bell, cls: "border-warning/40 bg-warning/12 text-warning", label: "Warning" },
  info: { icon: Info, cls: "border-accent/30 bg-accent/10 text-accent", label: "Info" },
} as const;

export function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<RiskItem[]>("/api/v1/predictions/high-risk?limit=20")
      .then((items) => {
        setNotifications((items ?? []).map((item, index) => {
          const score = item.risk_score;
          const severity: Notification["severity"] = score != null && score >= 85 ? "critical" : "warning";
          const confidence = item.confidence_score != null ? `${Math.round(item.confidence_score * 100)}% confidence` : "confidence N/A";
          return {
            id: String(item.id ?? item.asset_id ?? `risk-${index}`),
            title: `${item.asset_name ?? item.asset_id ?? "Asset"} requires review`,
            body: `Stored risk score ${score != null ? score.toFixed(1) : "N/A"} · ${item.risk_level ?? "risk class N/A"} · ${confidence}.`,
            severity,
            time: item.prediction_time ? new Date(item.prediction_time).toLocaleString() : "Timestamp N/A",
          };
        }));
      })
      .catch(() => setNotifications([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader eyebrow="System" title="Notifications" description="Live alerts derived from stored high-risk prediction records." />
        {loading ? (
          <div className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">Loading live alerts...</div>
        ) : (
          <ul className="space-y-3">
            {notifications.length === 0 ? (
              <li className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">No high-risk stored predictions are currently available.</li>
            ) : notifications.map((notification) => {
              const sev = severityMap[notification.severity];
              const Icon = sev.icon;
              return (
                <li key={notification.id} className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-4 rounded-lg border border-l-2 border-l-primary bg-card p-4">
                  <span className={`grid size-9 shrink-0 place-items-center rounded-md border ${sev.cls}`}><Icon className="size-4" /></span>
                  <div className="min-w-0">
                    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3"><p className="text-sm font-semibold">{notification.title}</p><p className="font-mono text-[11px] text-muted-foreground">{notification.time}</p></div>
                    <p className="mt-1 text-sm text-muted-foreground">{notification.body}</p>
                    <p className={`mt-2 eyebrow ${notification.severity === "critical" ? "text-danger" : "text-warning"}`}>{sev.label}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </DashboardLayout>
  );
}
