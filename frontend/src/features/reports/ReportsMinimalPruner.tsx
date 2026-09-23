import { useEffect } from "react";

const REMOVE_LABELS = [
  "evidence strength",
  "official structural condition",
  "official structural risk",
  "model validation",
  "model governance",
  "audit controls",
  "real evidence + model decision support",
  "prediction, recommendations & required evidence",
  "model governance prediction basis",
  "rul / deterioration horizon",
  "recommended actions",
  "what is necessary next",
  "evidence completeness",
  "required engineering inputs",
  "government-linked evidence",
  "records used by the selected-asset report",
  "official guidance references",
  "government documents used to frame recommendations",
  "interpretation boundary",
  "prediction controls are in digital twin.",
];

function norm(value: string | null | undefined) {
  return (value ?? "").replace(/\s+/g, " ").trim().toLowerCase();
}

function looksLikeSection(node: HTMLElement) {
  const rect = node.getBoundingClientRect();
  if (rect.width < 180 || rect.height < 40) return false;
  if (rect.width > window.innerWidth * 0.995) return false;

  const tag = node.tagName.toLowerCase();
  const cls =
    typeof node.className === "string" ? node.className.toLowerCase() : "";

  const style = window.getComputedStyle(node);
  const border =
    parseFloat(style.borderTopWidth || "0") +
    parseFloat(style.borderRightWidth || "0") +
    parseFloat(style.borderBottomWidth || "0") +
    parseFloat(style.borderLeftWidth || "0");

  return (
    ["section", "article"].includes(tag) ||
    cls.includes("card") ||
    cls.includes("panel") ||
    cls.includes("section") ||
    cls.includes("governance") ||
    cls.includes("decision") ||
    cls.includes("report") ||
    border > 0
  );
}

function findSectionRoot(start: HTMLElement): HTMLElement | null {
  let node: HTMLElement | null = start;
  let fallback: HTMLElement | null = null;

  for (let depth = 0; node && depth < 9; depth += 1, node = node.parentElement) {
    const text = norm(node.textContent);

    // Never remove the selected-report page/root or the export controls.
    if (
      text.includes("selected asset report") &&
      text.includes("download pdf") &&
      text.includes("download csv") &&
      text.includes("download json")
    ) {
      break;
    }

    if (
      text.includes("download pdf") ||
      text.includes("download csv") ||
      text.includes("download json")
    ) {
      continue;
    }

    if (looksLikeSection(node)) {
      const rect = node.getBoundingClientRect();

      // Prefer a local section rather than a huge wrapper.
      if (rect.height <= window.innerHeight * 0.72) {
        return node;
      }

      fallback ??= node;
    }
  }

  return fallback;
}

function removeVerboseReportSections() {
  const nodes = Array.from(document.querySelectorAll<HTMLElement>("body *"));

  for (const el of nodes) {
    const text = norm(el.textContent);
    if (!text) continue;

    const matched = REMOVE_LABELS.some(
      (label) => text === label || text.startsWith(label),
    );
    if (!matched) continue;

    const root = findSectionRoot(el);
    if (!root) continue;

    const rootText = norm(root.textContent);

    if (
      rootText.includes("download pdf") ||
      rootText.includes("download csv") ||
      rootText.includes("download json")
    ) {
      continue;
    }

    root.dataset.simrasRemovedVerboseReportSection = text.slice(0, 100);
    root.style.setProperty("display", "none", "important");
  }
}

export function ReportsMinimalPruner() {
  useEffect(() => {
    let frame = 0;

    const run = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(removeVerboseReportSections);
    };

    run();

    const observer = new MutationObserver(run);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    window.addEventListener("resize", run);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("resize", run);
    };
  }, []);

  return null;
}
