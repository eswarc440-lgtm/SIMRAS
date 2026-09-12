import { Link } from "@tanstack/react-router";
import { cn } from "../../lib/utils";

interface LogoProps {
  className?: string;
  tone?: "light" | "dark";
  showSub?: boolean;
  to?: string;
}

export function LogoMark({ className, tone = "dark" }: { className?: string; tone?: "light" | "dark" }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "grid size-9 shrink-0 place-items-center rounded-[6px] border",
        tone === "light" ? "border-navy-foreground/30" : "border-primary/25 bg-primary/8",
        className,
      )}
    >
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M2 18h20" strokeLinecap="round" />
        <path d="M12 3v15" strokeLinecap="round" />
        <path d="M12 4 3 18M12 4l9 14" strokeLinecap="round" />
        <path d="M7 11h10" strokeLinecap="round" />
      </svg>
    </span>
  );
}

export function Logo({ className, tone = "dark", showSub = false, to = "/" }: LogoProps) {
  return (
    <Link
      to={to}
      className={cn(
        "flex items-center gap-3 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring",
        tone === "light" ? "text-navy-foreground" : "text-foreground",
        className,
      )}
      aria-label="SIMRAS home"
    >
      <LogoMark tone={tone} />
      <span className="min-w-0">
        <span className="block font-display text-lg font-extrabold tracking-[0.14em] leading-none">SIMRAS</span>
        {showSub && (
          <span
            className={cn(
              "mt-1 block text-[10px] leading-tight tracking-wide",
              tone === "light" ? "text-navy-foreground/60" : "text-muted-foreground",
            )}
          >
            Structural Infrastructure
            <br />
            Monitoring System
          </span>
        )}
      </span>
    </Link>
  );
}
