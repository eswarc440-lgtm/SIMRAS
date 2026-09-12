import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  Activity,
  BarChart3,
  Bell,
  Box,
  Building2,
  ChevronDown,
  FileText,
  Gauge,
  LayoutDashboard,
  LogOut,
  Map,
  Menu,
  Settings,
  ShieldAlert,
  Sparkles,
  User,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "../components/ui/sheet";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { LogoMark } from "../components/common/Logo";
import { useAuth } from "../hooks/useAuth";
import { cn } from "../lib/utils";

type NavChild = { to: string; label: string; icon: React.ComponentType<{ className?: string }> };
type NavItem = { to: string; label: string; children?: NavChild[] };

export const topNav: NavItem[] = [
  { to: "/home", label: "Home" },
  {
    to: "/infrastructure",
    label: "Infrastructure",
    children: [
      { to: "/infrastructure", label: "Assets", icon: Building2 },
      { to: "/infrastructure/inspections", label: "Inspections", icon: Activity },
      { to: "/infrastructure/maintenance", label: "Maintenance", icon: ShieldAlert },
      { to: "/digital-twin", label: "Digital Twin", icon: Box },
      { to: "/gis", label: "GIS", icon: Map },
    ],
  },
  {
    to: "/ai",
    label: "AI Intelligence",
    children: [
      { to: "/ai", label: "AI Overview", icon: Sparkles },
      { to: "/ai/predictions", label: "Predictions", icon: Activity },
      { to: "/ai/risk-analysis", label: "Risk Analysis", icon: ShieldAlert },
      { to: "/ai/analytics", label: "Analytics", icon: BarChart3 },
      { to: "/ai/model-performance", label: "Model Performance", icon: Gauge },
    ],
  },
  { to: "/reports", label: "Reports" },
];

function useActive() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (to: string) => pathname === to || (to !== "/home" && pathname.startsWith(to + "/"));
}

function DesktopNav() {
  const isActive = useActive();
  const linkCls = (active: boolean) =>
    cn(
      "inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
      active ? "bg-primary/8 text-primary" : "text-foreground/70 hover:bg-muted hover:text-foreground",
    );

  return (
    <nav aria-label="Primary" className="hidden items-center gap-1 lg:flex">
      {topNav.map((item) =>
        item.children ? (
          <DropdownMenu key={item.label}>
            <DropdownMenuTrigger className={linkCls(item.children.some((c) => isActive(c.to)))}>
              {item.label}
              <ChevronDown className="size-3.5" aria-hidden="true" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-60">
              {item.children.map((child) => (
                <DropdownMenuItem key={child.to} asChild>
                  <Link to={child.to} className="flex items-center gap-2">
                    <child.icon className="size-4 text-muted-foreground" />
                    {child.label}
                  </Link>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Link key={item.to} to={item.to} className={linkCls(isActive(item.to))}>
            {item.label}
          </Link>
        ),
      )}
    </nav>
  );
}

function MobileNav({ onNavigate }: { onNavigate: () => void }) {
  const isActive = useActive();
  return (
    <nav aria-label="Primary mobile" className="flex flex-col gap-1 p-4">
      {topNav.map((item) => (
        <div key={item.label} className="mb-2">
          <Link
            to={item.to}
            onClick={onNavigate}
            className={cn(
              "block rounded-md px-3 py-2 text-sm font-semibold",
              isActive(item.to) ? "bg-primary/8 text-primary" : "text-foreground",
            )}
          >
            {item.label}
          </Link>
          {item.children && (
            <ul className="mt-1 space-y-0.5 border-l pl-3">
              {item.children.map((child) => (
                <li key={child.to}>
                  <Link
                    to={child.to}
                    onClick={onNavigate}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                      isActive(child.to) ? "text-primary" : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <child.icon className="size-4" />
                    {child.label}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
      <Link
        to="/dashboard"
        onClick={onNavigate}
        className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <LayoutDashboard className="size-4" />
        Dashboard
      </Link>
    </nav>
  );
}

export function TopBar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => setMobileOpen(false), [pathname]);

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto grid h-16 w-full max-w-[1600px] grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 sm:px-6 lg:grid-cols-[auto_minmax(0,1fr)_auto] lg:gap-6">
        <Link to="/home" className="flex min-w-0 items-center gap-2.5" aria-label="SIMRAS home">
          <LogoMark />
          <span className="min-w-0">
            <span className="block font-display text-base leading-none font-extrabold tracking-[0.14em]">SIMRAS</span>
            <span className="mt-1 hidden truncate text-[10px] leading-none text-muted-foreground sm:block">
              Structural Infrastructure Monitoring System
            </span>
          </span>
        </Link>

        <div className="hidden justify-center lg:flex">
          <DesktopNav />
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <Button asChild variant="ghost" size="icon" aria-label="Notifications" className="min-h-10 min-w-10">
            <Link to="/notifications">
              <Bell className="size-4" />
            </Link>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Account menu" className="min-h-10 min-w-10">
                <span className="grid size-8 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                  {user?.name?.charAt(0) ?? "S"}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="min-w-0">
                <span className="block truncate">{user?.name}</span>
                <span className="block truncate text-xs font-normal text-muted-foreground">
                  {user?.organization} · {user?.role}
                </span>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/dashboard" className="flex items-center gap-2">
                  <LayoutDashboard className="size-4" /> Dashboard
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/profile" className="flex items-center gap-2">
                  <User className="size-4" /> Profile
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/settings" className="flex items-center gap-2">
                  <Settings className="size-4" /> Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/reports" className="flex items-center gap-2">
                  <FileText className="size-4" /> Reports
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={() => {
                  logout();
                  navigate({ to: "/auth/login" });
                }}
                className="flex items-center gap-2"
              >
                <LogOut className="size-4" /> Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open navigation" className="min-h-10 min-w-10 lg:hidden">
                <Menu className="size-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[300px] p-0">
              <SheetTitle className="sr-only">SIMRAS navigation</SheetTitle>
              <div className="pt-10">
                <MobileNav onNavigate={() => setMobileOpen(false)} />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}

export function DashboardLayout({ children, bare = false }: { children: ReactNode; bare?: boolean }) {
  const { user, ready } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (ready && !user) navigate({ to: "/auth/login" });
  }, [ready, user, navigate]);

  if (!ready || !user) {
    return (
      <div className="grid min-h-screen place-items-center bg-background">
        <p className="text-sm text-muted-foreground">Loading SIMRAS workspace…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full bg-background">
      <TopBar />
      {bare ? (
        children
      ) : (
        <main className="mx-auto w-full max-w-[1600px] min-w-0 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      )}
    </div>
  );
}
