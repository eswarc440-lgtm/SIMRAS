import { Link } from "@tanstack/react-router";
import { ArrowRight, Layers, Search, ZoomIn, ZoomOut, Crosshair, ListFilter } from "lucide-react";
import { Reveal, SectionHeading } from "../common/Reveal";
import { Button } from "../ui/button";
import digitalTwinImage from "../../assets/digital-twin.jpg";

export function DigitalTwinSection() {
  return (
    <section id="digital-twin" className="border-b bg-background py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading
            eyebrow="Digital Twin"
            title="See Infrastructure as a Living System."
            description="A geometry-accurate digital representation of bridges, roads, buildings and utilities — enriched with condition, risk and prediction data from the SIMRAS intelligence layer."
          />
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-12 overflow-hidden rounded-xl border bg-navy shadow-elevated">
            <div className="flex items-center justify-between gap-3 border-b border-navy-foreground/10 px-4 py-3">
              <p className="eyebrow text-navy-foreground/50">Digital Twin View</p>
              <div className="flex gap-1.5" aria-hidden="true">
                <span className="size-2 rounded-full bg-success" />
                <span className="size-2 rounded-full bg-warning" />
                <span className="size-2 rounded-full bg-danger" />
              </div>
            </div>
            <div className="relative">
              <img
                src={digitalTwinImage}
                alt="Wireframe 3D digital twin of a city with bridges, highways and buildings"
                loading="lazy"
                width={1600}
                height={1008}
                className="aspect-[16/10] w-full object-cover"
              />
              <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-navy to-transparent p-4 sm:p-6">
                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    { k: "Assets in model", v: "1,284" },
                    { k: "Structural layers", v: "12" },
                    { k: "Live risk overlays", v: "4" },
                  ].map((s) => (
                    <div key={s.k} className="rounded-md border border-navy-foreground/12 bg-navy/70 px-3 py-2 backdrop-blur">
                      <p className="eyebrow text-navy-foreground/45">{s.k}</p>
                      <p className="mt-1 font-display text-lg font-bold text-navy-foreground tabular-nums">{s.v}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </Reveal>

        <Reveal delay={0.16}>
          <div className="mt-8">
            <Button asChild variant="outline" size="lg" className="min-h-11">
              <Link to="/digital-twin">
                Explore Digital Twin
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

export function GISSection() {
  return (
    <section id="gis" className="border-b bg-surface py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:items-center">
          <Reveal>
            <SectionHeading
              eyebrow="GIS Intelligence"
              title="Understand Infrastructure in Its Real-World Context."
              description="Every asset is mapped, layered and risk-scored in space. Spatial clustering reveals corridor-level exposure that asset-by-asset review cannot."
            />
            <ul className="mt-8 space-y-3 text-sm text-muted-foreground">
              {[
                "Asset markers with live condition state",
                "Risk zones, corridors and district boundaries",
                "Layer control for roads, bridges, buildings and utilities",
                "GeoJSON contract ready for PostGIS integration",
              ].map((i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden="true" />
                  {i}
                </li>
              ))}
            </ul>
            <div className="mt-8">
              <Button asChild size="lg" className="min-h-11">
                <Link to="/gis">
                  Open GIS Workspace
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
            </div>
          </Reveal>

          <Reveal delay={0.12}>
            <div className="overflow-hidden rounded-xl border bg-card shadow-elevated">
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 border-b px-3 py-2.5">
                <div className="flex min-w-0 items-center gap-2 rounded-md border bg-muted px-2.5 py-1.5">
                  <Search className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="truncate text-xs text-muted-foreground">Search infrastructure…</span>
                </div>
                <div className="flex shrink-0 items-center gap-1 text-muted-foreground">
                  {[ZoomIn, ZoomOut, Layers, ListFilter, Crosshair].map((Icon, i) => (
                    <span key={i} className="grid size-7 place-items-center rounded border" aria-hidden="true">
                      <Icon className="size-3.5" />
                    </span>
                  ))}
                </div>
              </div>

              <div className="relative aspect-[4/3] bg-muted">
                <div className="grid-lines absolute inset-0 opacity-70" aria-hidden="true" />
                <svg viewBox="0 0 400 300" className="absolute inset-0 size-full" aria-hidden="true">
                  <path d="M0 210 C 90 190, 150 240, 400 170" stroke="var(--color-border)" strokeWidth="10" fill="none" />
                  <path d="M0 210 C 90 190, 150 240, 400 170" stroke="var(--color-muted-foreground)" strokeWidth="1.5" strokeDasharray="8 8" fill="none" opacity="0.5" />
                  <path d="M60 300 C 90 190, 140 120, 130 0" stroke="var(--color-border)" strokeWidth="8" fill="none" />
                  <path d="M300 300 C 290 200, 330 120, 380 0" stroke="var(--color-border)" strokeWidth="6" fill="none" />
                  <circle cx="200" cy="140" r="58" fill="var(--color-danger)" opacity="0.08" />
                  <circle cx="120" cy="215" r="42" fill="var(--color-warning)" opacity="0.1" />
                </svg>
                {[
                  { x: "50%", y: "46%", tone: "bg-danger", label: "BL-302" },
                  { x: "30%", y: "72%", tone: "bg-warning", label: "RD-204" },
                  { x: "68%", y: "60%", tone: "bg-success", label: "BR-221" },
                  { x: "76%", y: "28%", tone: "bg-success", label: "WT-233" },
                  { x: "22%", y: "34%", tone: "bg-warning", label: "UT-407" },
                ].map((m) => (
                  <span
                    key={m.label}
                    className="absolute -translate-x-1/2 -translate-y-1/2"
                    style={{ left: m.x, top: m.y }}
                  >
                    <span className={`block size-3 rounded-full ring-4 ring-card ${m.tone}`} aria-hidden="true" />
                    <span className="mt-1 block font-mono text-[10px] text-muted-foreground">{m.label}</span>
                  </span>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-4 border-t px-4 py-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-success" /> Healthy
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-warning" /> Warning
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-danger" /> Critical
                </span>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
