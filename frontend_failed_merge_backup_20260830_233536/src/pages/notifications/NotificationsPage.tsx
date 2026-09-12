import { useEffect, useState } from "react";
import { AlertTriangle, Bell, Info } from "lucide-react";
import { DashboardLayout } from "../../layouts/DashboardLayout";
import { PageHeader } from "../../components/common/PageHeader";
import { apiRequest } from "../../services/api";

const severityMap = {
  critical: { icon: AlertTriangle, cls: "border-danger/30 bg-danger/10 text-danger", label: "Critical" },
  warning: { icon: Bell, cls: "border-warning/40 bg-warning/12 text-warning", label: "Warning" },
  info: { icon: Info, cls: "border-accent/30 bg-accent/10 text-accent", label: "Info" },
} as const;

export function NotificationsPage() {
  const [notifications, setNotifications] = useState<Array<{ id: string; title: string; body: string; severity: "critical" | "warning" | "info"; time: string; read: boolean }>>([]);

  useEffect(() => {
    apiRequest<Array<{ id: string; name: string; district: string; risk_score: number; health_score: number }>>('/api/v1/analytics/high-risk')
      .then((items) => {
        const next = (items ?? []).slice(0, 8).map((item, index) => ({
          id: item.id || `risk-${index}`,
          title: `${item.name || 'High-risk asset'} requires review`,
          body: `${item.name || 'Asset'} in ${item.district || 'AP'} has a ${Number(item.risk_score || 0).toFixed(1)} risk score and ${Number(item.health_score || 0).toFixed(0)} health score.`,
          severity: (Number(item.risk_score || 0) >= 80 ? 'critical' : 'warning') as 'critical' | 'warning',
          time: 'Live',
          read: false,
        }));
        setNotifications(next);
      })
      .catch((error) => console.error('Notifications fetch failed', error));
  }, []);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader
          eyebrow="System"
          title="Notifications"
          description="Risk alerts, inspection reminders and platform updates."
        />

        <ul className="space-y-3">
          {notifications.length === 0 ? (
            <li className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">No live alerts are currently available.</li>
          ) : notifications.map((n) => {
            const sev = severityMap[n.severity];
            const Icon = sev.icon;
            return (
              <li
                key={n.id}
                className={`grid grid-cols-[auto_minmax(0,1fr)] items-start gap-4 rounded-lg border bg-card p-4 ${
                  n.read ? "" : "border-l-2 border-l-primary"
                }`}
              >
                <span className={`grid size-9 shrink-0 place-items-center rounded-md border ${sev.cls}`}>
                  <Icon className="size-4" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                    <p className="min-w-0 text-sm font-semibold">{n.title}</p>
                    <p className="shrink-0 font-mono text-[11px] text-muted-foreground">{n.time}</p>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{n.body}</p>
                  <p className={`mt-2 eyebrow ${n.severity === "critical" ? "text-danger" : n.severity === "warning" ? "text-warning" : "text-accent"}`}>
                    {sev.label}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </DashboardLayout>
  );
}



