import { Link } from "@tanstack/react-router";
import { Logo } from "../common/Logo";

const columns = [
  { title: "Platform", items: ["AI Intelligence", "Digital Twin", "GIS", "Infrastructure", "Analytics"] },
  { title: "Resources", items: ["Reports", "Documentation", "Technology"] },
  { title: "Company", items: ["About", "Contact"] },
  { title: "Legal", items: ["Privacy", "Terms"] },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-navy-foreground/10 bg-navy text-navy-foreground">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8 lg:py-16">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,2fr)]">
          <div className="min-w-0">
            <Logo tone="light" />
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-navy-foreground/60">
              Structural Infrastructure Monitoring and Risk Assistance System
            </p>
            <p className="mt-6 eyebrow text-accent">Monitor. Predict. Protect.</p>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            {columns.map((col) => (
              <div key={col.title}>
                <h3 className="eyebrow text-navy-foreground/50">{col.title}</h3>
                <ul className="mt-4 space-y-2.5">
                  {col.items.map((item) => (
                    <li key={item}>
                      <Link
                        to="/auth/login"
                        className="text-sm text-navy-foreground/75 transition-colors hover:text-navy-foreground"
                      >
                        {item}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-navy-foreground/10 pt-6">
          <p className="text-xs text-navy-foreground/50">© 2026 SIMRAS. All rights reserved.</p>
          <p className="text-xs text-navy-foreground/40">Demonstration data. Not real infrastructure records.</p>
        </div>
      </div>
    </footer>
  );
}
