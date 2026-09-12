import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "../ui/button";
import { Reveal } from "../common/Reveal";
import ctaImage from "../../assets/cta-infrastructure.jpg";

export function FinalCTA() {
  return (
    <section className="relative overflow-hidden bg-navy py-24 text-navy-foreground sm:py-32">
      <img
        src={ctaImage}
        alt="Elevated metro viaduct and highway interchange at night"
        loading="lazy"
        width={1920}
        height={912}
        className="absolute inset-0 size-full object-cover opacity-45"
      />
      <div className="absolute inset-0 bg-gradient-to-r from-navy via-navy/80 to-navy/40" aria-hidden="true" />

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <div className="max-w-2xl">
            <p className="eyebrow text-accent">Monitor. Predict. Protect.</p>
            <h2 className="text-hero mt-5 text-4xl text-balance sm:text-5xl lg:text-6xl">
              Build Safer Infrastructure Through Intelligence.
            </h2>
            <p className="mt-6 text-base leading-relaxed text-navy-foreground/70 sm:text-lg">
              SIMRAS connects monitoring, AI, GIS and digital twin technologies into one intelligent infrastructure
              platform.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Button asChild size="lg" className="min-h-11">
                <Link to="/auth/register">
                  Explore SIMRAS
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="min-h-11 border-navy-foreground/25 bg-navy-foreground/5 text-navy-foreground hover:bg-navy-foreground/12 hover:text-navy-foreground"
              >
                <Link to="/auth/login">Request Access</Link>
              </Button>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
