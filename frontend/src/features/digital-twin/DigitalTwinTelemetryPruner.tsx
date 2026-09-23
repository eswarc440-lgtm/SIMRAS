import { useEffect } from "react";

const REQUIRED_TOKENS = [
  "reservoir telemetry",
  "water level",
  "current storage",
  "reservoir capacity",
];

const OPTIONAL_TOKENS = [
  "digital screen",
  "temperature",
  "storage utilisation",
  "reservoir observation",
  "hide dimensions",
];

function normalize(text: string) {
  return text.toLowerCase().replace(/\s+/g, " ").trim();
}

function looksLikeTelemetryCard(text: string) {
  const value = normalize(text);

  if (!value.includes("reservoir telemetry")) return false;

  const requiredHits = REQUIRED_TOKENS.filter((token) =>
    value.includes(token),
  ).length;

  const optionalHits = OPTIONAL_TOKENS.filter((token) =>
    value.includes(token),
  ).length;

  return requiredHits >= 3 || (requiredHits >= 2 && optionalHits >= 2);
}

function findTelemetryContainer(start: HTMLElement) {
  let node: HTMLElement | null = start;
  let best: HTMLElement | null = null;

  for (let depth = 0; node && depth < 8; depth += 1) {
    const text = node.innerText || node.textContent || "";

    if (looksLikeTelemetryCard(text)) {
      const rect = node.getBoundingClientRect();

      // Large enough to be the telemetry card, but never the whole page/workspace.
      if (
        rect.width >= 300 &&
        rect.width <= 1200 &&
        rect.height >= 180 &&
        rect.height <= 700
      ) {
        best = node;
      }
    }

    node = node.parentElement;
  }

  return best;
}

function removeTelemetryCard() {
  const candidates = Array.from(
    document.querySelectorAll<HTMLElement>(
      "section, article, aside, div",
    ),
  );

  for (const element of candidates) {
    const text = element.innerText || element.textContent || "";

    if (!looksLikeTelemetryCard(text)) continue;

    const container = findTelemetryContainer(element);

    if (container) {
      container.dataset.simrasTelemetryRemoved = "true";
      container.style.setProperty("display", "none", "important");
      container.setAttribute("aria-hidden", "true");
      return;
    }
  }
}

export function DigitalTwinTelemetryPruner() {
  useEffect(() => {
    let queued = false;

    const run = () => {
      queued = false;
      removeTelemetryCard();
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

export default DigitalTwinTelemetryPruner;