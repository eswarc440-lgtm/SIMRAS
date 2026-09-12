import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

export function Reveal({
  children,
  delay = 0,
  y = 24,
  className,
}: {
  children: ReactNode;
  delay?: number;
  y?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  tone = "dark",
  align = "left",
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  tone?: "light" | "dark";
  align?: "left" | "center";
}) {
  const muted = tone === "light" ? "text-navy-foreground/70" : "text-muted-foreground";
  return (
    <div className={align === "center" ? "mx-auto max-w-3xl text-center" : "max-w-3xl"}>
      {eyebrow && <p className={`eyebrow ${tone === "light" ? "text-accent" : "text-primary"}`}>{eyebrow}</p>}
      <h2 className="mt-3 font-display text-3xl font-bold tracking-tight text-balance sm:text-4xl lg:text-[2.75rem]">
        {title}
      </h2>
      {description && <p className={`mt-4 text-base leading-relaxed ${muted}`}>{description}</p>}
    </div>
  );
}
