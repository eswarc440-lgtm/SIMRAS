import { Link, useRouterState } from "@tanstack/react-router";
import { cn } from "../../lib/utils";

const tabs = [
  { to: "/ai", label: "Overview" },
  { to: "/ai/predictions", label: "Predictions" },
  { to: "/ai/risk-analysis", label: "Risk Analysis" },
  { to: "/ai/analytics", label: "Analytics" },
  { to: "/ai/model-performance", label: "Model Performance" },
] as const;

export function AITabs() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <nav aria-label="AI Intelligence sections" className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
      <ul className="flex min-w-max gap-1 border-b">
        {tabs.map((t) => {
          const active = pathname === t.to;
          return (
            <li key={t.to}>
              <Link
                to={t.to}
                className={cn(
                  "-mb-px block border-b-2 px-3 py-2.5 text-sm transition-colors",
                  active
                    ? "border-primary font-medium text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground",
                )}
              >
                {t.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
