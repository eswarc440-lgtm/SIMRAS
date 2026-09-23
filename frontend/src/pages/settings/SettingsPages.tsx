import { DashboardLayout } from "../../layouts/DashboardLayout";
import { ChartCard, PageHeader } from "../../components/common/PageHeader";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import { Separator } from "../../components/ui/separator";
import { useAuth } from "../../hooks/useAuth";

export function ProfilePage() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader eyebrow="System" title="Profile" description="Your SIMRAS account and organisation details." />

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <ChartCard title="Account" subtitle="Identity and role">
            <div className="flex items-center gap-4">
              <span className="grid size-16 shrink-0 place-items-center rounded-full bg-primary font-display text-xl font-bold text-primary-foreground">
                {user.name.charAt(0)}
              </span>
              <div className="min-w-0">
                <p className="truncate text-lg font-semibold">{user.name}</p>
                <p className="truncate text-sm text-muted-foreground">{user.role}</p>
              </div>
            </div>
            <dl className="mt-6 space-y-3 border-t pt-5 text-sm">
              {[
                { k: "Email", v: user.email },
                { k: "Phone", v: user.phone },
                { k: "Organization", v: user.organization },
                { k: "Role", v: user.role },
              ].map((r) => (
                <div key={r.k} className="grid grid-cols-[minmax(0,1fr)_auto] gap-3">
                  <dt className="text-muted-foreground">{r.k}</dt>
                  <dd className="min-w-0 truncate text-right font-medium">{r.v}</dd>
                </div>
              ))}
            </dl>
          </ChartCard>

          <ChartCard title="Edit Profile" subtitle="Update your contact details">
            <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="pf-name">Full Name</Label>
                  <Input id="pf-name" defaultValue={user.name} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pf-email">Email</Label>
                  <Input id="pf-email" type="email" defaultValue={user.email} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pf-phone">Phone</Label>
                  <Input id="pf-phone" defaultValue={user.phone} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pf-org">Organization</Label>
                  <Input id="pf-org" defaultValue={user.organization} />
                </div>
              </div>
              <div className="flex flex-wrap gap-2 pt-2">
                <Button type="submit">Save Changes</Button>
                <Button type="button" variant="outline">
                  Change Password
                </Button>
                <Button type="button" variant="outline">
                  Security
                </Button>
              </div>
            </form>
          </ChartCard>
        </div>
      </div>
    </DashboardLayout>
  );
}

export function SettingsPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader eyebrow="System" title="Settings" description="Account, security, notification and appearance preferences." />

        <div className="grid gap-4 xl:grid-cols-2">
          <ChartCard title="Account" subtitle="Workspace defaults">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="st-region">Default region</Label>
                <Input id="st-region" defaultValue="All regions" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="st-lang">Language</Label>
                <Input id="st-lang" defaultValue="English (India)" />
              </div>
            </div>
          </ChartCard>

          <ChartCard title="Security" subtitle="Authentication and sessions">
            <div className="space-y-4">
              {[
                { id: "mfa", label: "Two-factor authentication", desc: "Require OTP on every sign-in", on: true },
                { id: "sessions", label: "Single active session", desc: "Sign out other devices automatically", on: false },
              ].map((s) => (
                <div key={s.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4">
                  <div className="min-w-0">
                    <Label htmlFor={s.id}>{s.label}</Label>
                    <p className="mt-0.5 text-xs text-muted-foreground">{s.desc}</p>
                  </div>
                  <Switch id={s.id} defaultChecked={s.on} />
                </div>
              ))}
              <Separator />
              <Button variant="outline">Manage Sessions</Button>
            </div>
          </ChartCard>

          <ChartCard title="Notifications" subtitle="Alert delivery preferences">
            <div className="space-y-4">
              {[
                { id: "n-risk", label: "AI risk alerts", desc: "High-risk escalations from the prediction engine", on: true },
                { id: "n-insp", label: "Inspection reminders", desc: "Upcoming and overdue inspections", on: true },
                { id: "n-sys", label: "System updates", desc: "Platform and model deployment notices", on: false },
              ].map((s) => (
                <div key={s.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4">
                  <div className="min-w-0">
                    <Label htmlFor={s.id}>{s.label}</Label>
                    <p className="mt-0.5 text-xs text-muted-foreground">{s.desc}</p>
                  </div>
                  <Switch id={s.id} defaultChecked={s.on} />
                </div>
              ))}
            </div>
          </ChartCard>

          <ChartCard title="Appearance" subtitle="Interface theme">
            <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4">
              <div className="min-w-0">
                <Label htmlFor="theme">Dark interface</Label>
                <p className="mt-0.5 text-xs text-muted-foreground">Optimised for control-room environments</p>
              </div>
              <Switch
                id="theme"
                onCheckedChange={(v) => document.documentElement.classList.toggle("dark", v)}
              />
            </div>
          </ChartCard>
        </div>
      </div>
    </DashboardLayout>
  );
}
