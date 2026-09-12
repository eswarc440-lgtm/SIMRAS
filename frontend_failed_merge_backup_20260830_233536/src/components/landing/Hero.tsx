import { Link } from "@tanstack/react-router";
import { motion, useReducedMotion } from "motion/react";
import { ArrowDown, ArrowRight } from "lucide-react";
import { Button } from "../ui/button";
import heroImage from "../../assets/hero-infrastructure.jpg";

/**
 * Cinematic hero.
 * `videoSrc` is optional: drop an MP4 in src/assets/videos and pass it here to
 * switch from the poster image to full-motion background video.
 */
export function Hero({ videoSrc }: { videoSrc?: string }) {
  const reduce = useReducedMotion();
  const fade = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 18 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.9, delay, ease: [0.16, 1, 0.3, 1] as const },
  });

  return (
    <section className="relative flex h-svh items-center overflow-hidden bg-navy">
      <div className="absolute inset-0">
        {videoSrc ? (
          <video
            className="size-full object-cover"
            src={videoSrc}
            poster={heroImage}
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
            aria-hidden="true"
          />
        ) : (
          <img
            src={heroImage}
            alt="Cable-stayed bridge and city skyline at dusk"
            width={1920}
            height={1088}
            className="size-full object-cover"
          />
        )}
        <div className="absolute inset-0 bg-navy/25" aria-hidden="true" />
        <div
          className="absolute inset-0 bg-gradient-to-t from-navy/80 via-navy/20 to-navy/40"
          aria-hidden="true"
        />
        <div className="grid-lines absolute inset-0 opacity-[0.04]" aria-hidden="true" />
      </div>

      <div className="relative mx-auto w-full max-w-7xl px-4 pt-28 pb-24 sm:px-6 lg:px-8">
        <motion.p {...fade(0.1)} className="eyebrow text-accent">
          SIMRAS
        </motion.p>

        <motion.h1
          {...fade(0.22)}
          className="text-hero mt-5 max-w-4xl text-[2.5rem] text-navy-foreground text-balance sm:text-6xl lg:text-7xl"
        >
          Structural Infrastructure Monitoring &amp; Intelligence
        </motion.h1>

        <motion.p
          {...fade(0.36)}
          className="mt-6 font-mono text-sm tracking-[0.28em] text-accent uppercase sm:text-base"
        >
          Monitor. Predict. Protect.
        </motion.p>

        <motion.p {...fade(0.46)} className="mt-6 max-w-xl text-base leading-relaxed text-navy-foreground/70 sm:text-lg">
          AI-powered infrastructure monitoring and risk assistance for smarter, earlier and better informed decisions.
        </motion.p>

        <motion.div {...fade(0.58)} className="mt-10 flex flex-wrap gap-3">
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
            <Link to="/digital-twin">View Digital Twin</Link>
          </Button>
        </motion.div>

        <motion.div {...fade(0.8)} className="mt-16 flex items-center gap-2 text-navy-foreground/45">
          <ArrowDown className="size-4" aria-hidden="true" />
          <span className="eyebrow">Scroll</span>
        </motion.div>
      </div>
    </section>
  );
}
