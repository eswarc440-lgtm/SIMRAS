import { Reveal, SectionHeading } from "../common/Reveal";

const pillars = [
  { no: "01", title: "Monitor", body: "Understand infrastructure conditions continuously across the entire asset portfolio." },
  { no: "02", title: "Analyze", body: "Turn inspection, sensor and spatial data into meaningful engineering insight." },
  { no: "03", title: "Predict", body: "Identify potential structural risks before they escalate into failures." },
  { no: "04", title: "Assist", body: "Support informed infrastructure decisions with evidence and confidence scores." },
];

export function PlatformIntro() {
  return (
    <section id="platform" className="border-b bg-background py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <SectionHeading
            eyebrow="The Platform"
            title="Infrastructure Intelligence, Built for Better Decisions."
            description="SIMRAS gives infrastructure authorities, engineers and planners a single operational view of asset condition, structural risk and spatial context — grounded in inspection data and machine learning."
          />
        </Reveal>

        <div className="mt-14 grid gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-2 lg:grid-cols-4">
          {pillars.map((p, i) => (
            <Reveal key={p.no} delay={i * 0.08} className="bg-card">
              <div className="h-full p-6 lg:p-8">
                <p className="font-mono text-xs text-primary">{p.no}</p>
                <h3 className="mt-6 font-display text-xl font-bold tracking-tight uppercase">{p.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
