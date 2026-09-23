import { useEffect, useState } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import { Menu, X } from "lucide-react";
import { Button } from "../ui/button";
import { Logo } from "../common/Logo";
import { cn } from "../../lib/utils";

const links = [
  { label: "Platform", hash: "#platform" },
  { label: "AI Intelligence", hash: "#ai" },
  { label: "Digital Twin", hash: "#digital-twin" },
  { label: "GIS", hash: "#gis" },
  { label: "Infrastructure", hash: "#infrastructure" },
  { label: "About", hash: "#impact" },
];

export function PublicNav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => setOpen(false), [pathname]);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-all duration-300",
        scrolled ? "border-b border-navy-foreground/10 bg-navy/92 shadow-elevated backdrop-blur-md" : "bg-transparent",
      )}
    >
      <nav
        aria-label="Main"
        className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:h-18 lg:px-8"
      >
        <Logo tone="light" />

        <ul className="hidden items-center gap-7 lg:flex">
          {links.map((l) => (
            <li key={l.label}>
              <a
                href={l.hash}
                className="text-sm text-navy-foreground/75 transition-colors hover:text-navy-foreground"
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="hidden items-center gap-2 lg:flex">
          <Button asChild variant="ghost" className="text-navy-foreground hover:bg-navy-foreground/10 hover:text-navy-foreground">
            <Link to="/auth/login">Login</Link>
          </Button>
          <Button asChild>
            <Link to="/auth/register">Get Started</Link>
          </Button>
        </div>

        <Button
          variant="ghost"
          size="icon"
          aria-label={open ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="min-h-11 min-w-11 text-navy-foreground hover:bg-navy-foreground/10 hover:text-navy-foreground lg:hidden"
        >
          {open ? <Menu className="size-5 rotate-90 transition-transform" /> : <Menu className="size-5" />}
        </Button>
      </nav>

      {open && (
        <div className="border-t border-navy-foreground/10 bg-navy lg:hidden">
          <div className="mx-auto max-w-7xl px-4 pt-2 pb-6 sm:px-6">
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="icon"
                aria-label="Close navigation menu"
                onClick={() => setOpen(false)}
                className="min-h-11 min-w-11 text-navy-foreground hover:bg-navy-foreground/10 hover:text-navy-foreground"
              >
                <X className="size-5" />
              </Button>
            </div>
            <ul className="divide-y divide-navy-foreground/10 border-y border-navy-foreground/10">
              {links.map((l) => (
                <li key={l.label}>
                  <a
                    href={l.hash}
                    onClick={() => setOpen(false)}
                    className="block py-3.5 text-base text-navy-foreground/85"
                  >
                    {l.label}
                  </a>
                </li>
              ))}
            </ul>
            <div className="mt-5 grid gap-2">
              <Button asChild variant="outline" className="border-navy-foreground/25 bg-transparent text-navy-foreground hover:bg-navy-foreground/10 hover:text-navy-foreground">
                <Link to="/auth/login">Login</Link>
              </Button>
              <Button asChild>
                <Link to="/auth/register">Get Started</Link>
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
