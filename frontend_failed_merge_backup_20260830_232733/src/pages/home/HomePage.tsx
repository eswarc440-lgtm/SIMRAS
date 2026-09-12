import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { ArrowRight, HardHat, Sparkles } from "lucide-react";
import { Button } from "../../components/ui/button";
import { DashboardLayout } from "../../layouts/DashboardLayout";

import bridgeArch from "../../assets/infra/bridge-arch.jpg.asset.json";
import bridgeCable from "../../assets/infra/bridge-cable.jpg.asset.json";
import roadHighway from "../../assets/infra/road-highway.jpg.asset.json";
import roadGhat from "../../assets/infra/road-ghat.jpg.asset.json";
import damSpillway from "../../assets/infra/dam-spillway.jpg.asset.json";
import damMist from "../../assets/infra/dam-mist.jpg.asset.json";
import civicBuilding from "../../assets/infra/civic-building.jpg.asset.json";
import barrage from "../../assets/infra/barrage.jpg.asset.json";

const slides = [
  { src: bridgeCable.url, alt: "Cable-stayed bridge pylon at dusk" },
  { src: bridgeArch.url, alt: "Steel arch rail bridge over a river" },
  { src: damSpillway.url, alt: "Dam spillway releasing water" },
  { src: roadHighway.url, alt: "Highway bypass corridor" },
  { src: civicBuilding.url, alt: "Government civic building" },
  { src: damMist.url, alt: "Reservoir dam at dawn" },
  { src: roadGhat.url, alt: "Aerial view of a winding ghat road" },
  { src: barrage.url, alt: "Barrage across a wide river" },
];

export function HomePage() {
  const reduce = useReducedMotion();
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (reduce) return;
    const id = setInterval(() => setIndex((i) => (i + 1) % slides.length), 5500);
    return () => clearInterval(id);
  }, [reduce]);

  return (
    <DashboardLayout bare>
      <main className="relative flex h-[calc(100svh-4rem)] w-full items-center overflow-hidden bg-foreground">
        {/* Slideshow */}
        <div className="absolute inset-0" aria-hidden="true">
          <AnimatePresence initial={false}>
            <motion.img
              key={slides[index]!.src}
              src={slides[index]!.src}
              alt={slides[index]!.alt}
              initial={{ opacity: 0, scale: 1.08 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ opacity: { duration: 1.4 }, scale: { duration: 7, ease: "linear" } }}
              className="absolute inset-0 size-full object-cover"
            />
          </AnimatePresence>
          <div className="absolute inset-0 bg-gradient-to-b from-black/45 via-black/10 to-black/55" />
        </div>

        {/* Content */}
        <div className="relative mx-auto flex w-full max-w-4xl flex-col items-center px-4 py-20 text-center sm:px-6">
          <motion.p
            initial={reduce ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="eyebrow text-primary-foreground/80"
          >
            Welcome to SIMRAS
          </motion.p>
          <motion.h1
            initial={reduce ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-hero mt-4 text-[2rem] text-balance text-primary-foreground sm:text-5xl lg:text-6xl"
          >
            Structural Infrastructure Monitoring System
          </motion.h1>
          <motion.p
            initial={reduce ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="mt-6 max-w-2xl text-sm leading-relaxed text-primary-foreground/85 sm:text-base"
          >
            Monitor infrastructure health, assess structural risks, and leverage AI-powered intelligence to support
            safer infrastructure decisions.
          </motion.p>

          <motion.div
            initial={reduce ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.3 }}
            className="mt-10 flex w-full flex-col items-center justify-center gap-4 sm:w-auto sm:flex-row"
          >
            <Button asChild size="lg" variant="secondary" className="min-h-12 w-full px-8 sm:w-auto">
              <Link to="/infrastructure">
                <HardHat className="size-4" />
                INFRASTRUCTURE
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button asChild size="lg" className="min-h-12 w-full px-8 sm:w-auto">
              <Link to="/ai">
                <Sparkles className="size-4" />
                AI INTELLIGENCE
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </motion.div>

          {/* Slide indicators */}
          <div className="mt-12 flex items-center gap-2">
            {slides.map((s, i) => (
              <button
                key={s.src}
                type="button"
                aria-label={`Show slide ${i + 1}`}
                onClick={() => setIndex(i)}
                className={
                  i === index
                    ? "h-1.5 w-8 rounded-full bg-primary-foreground transition-all"
                    : "h-1.5 w-3 rounded-full bg-primary-foreground/40 transition-all hover:bg-primary-foreground/70"
                }
              />
            ))}
          </div>
        </div>
      </main>
    </DashboardLayout>
  );
}
