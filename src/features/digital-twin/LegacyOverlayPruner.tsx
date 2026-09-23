import { useEffect } from "react";

const SPEC_TOKENS = [
  "runway width",
  "runway length",
  "runway designation",
  "runway true bearing",
  "surface: asphalt",
  "gate count",
  "gate width",
  "deck width",
  "constructed year",
  "scour sluice",
  "left scour",
  "right scour",
  "length m:",
  "height m:",
  "width m:",
  "capacity:",
  "spillway",
  "crest level",
  "bridge length",
  "bridge width",
  "number of spans",
];

const KEEP_TOKENS = [
  "health score",
  "risk score",
  "remaining life",
  "prediction",
  "evidence",
  "report",
  "gis command",
  "digital twin",
];

function isSpecOverlayText(text: string) {
  const normalized = text.toLowerCase().replace(/\s+/g, " ").trim();

  if (!normalized) return false;
  if (KEEP_TOKENS.some((token) => normalized.includes(token))) return false;

  let hits = 0;

  for (const token of SPEC_TOKENS) {
    if (normalized.includes(token)) hits += 1;
  }

  if (
    normalized.includes("runway designation") ||
    normalized.includes("runway true bearing") ||
    normalized.includes("scour sluice")
  ) {
    return true;
  }

  return hits >= 2;
}

function findSafeContainer(node: HTMLElement) {
  let current: HTMLElement | null = node;

  for (let i = 0; current && i < 6; i += 1) {
    const text = (current.innerText || current.textContent || "").trim();

    if (isSpecOverlayText(text)) {
      const rect = current.getBoundingClientRect();

      if (
        rect.width > 0 &&
        rect.height > 0 &&
        rect.width <= 900 &&
        rect.height <= 220
      ) {
        return current;
      }
    }

    current = current.parentElement;
  }

  return null;
}

function pruneLegacySpecificationBoxes() {
  const candidates = Array.from(
    document.querySelectorAll<HTMLElement>(
      "div, section, aside, article, p, span"
    )
  );

  for (const element of candidates) {
    const text = (element.innerText || element.textContent || "").trim();

    if (!isSpecOverlayText(text)) continue;

    const container = findSafeContainer(element);

    if (container) {
      container.dataset.simrasLegacySpecOverlayRemoved = "true";
      container.style.setProperty("display", "none", "important");
    }
  }
}

export function LegacyOverlayPruner() {
  useEffect(() => {
    let queued = false;

    const run = () => {
      queued = false;
      pruneLegacySpecificationBoxes();
    };

    const schedule = () => {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(run);
    };

    schedule();

    const observer = new MutationObserver(schedule);

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    window.addEventListener("resize", schedule);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", schedule);
    };
  }, []);

  return null;
}

export default LegacyOverlayPruner;