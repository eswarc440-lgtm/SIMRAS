import { useEffect } from "react";

function norm(value: string | null | undefined) {
  return (value ?? "").replace(/\s+/g, " ").trim().toLowerCase();
}

const BUTTON_LABELS = new Set([
  "download pdf",
  "download csv",
  "download json",
]);

function hideExportButtons() {
  const buttons = Array.from(
    document.querySelectorAll<HTMLElement>("button, a, [role='button']"),
  );

  for (const el of buttons) {
    if (BUTTON_LABELS.has(norm(el.textContent))) {
      el.style.setProperty("display", "none", "important");
      el.dataset.simrasHiddenReportExport = "true";
    }
  }
}

function hideScopeCard() {
  const nodes = Array.from(document.querySelectorAll<HTMLElement>("body *"));

  for (const el of nodes) {
    const text = norm(el.textContent);

    if (
      text !== "selected_asset_only" &&
      text !== "selected asset only" &&
      text !== "no portfolio aggregation"
    ) {
      continue;
    }

    let node: HTMLElement | null = el;
    for (let depth = 0; node && depth < 6; depth += 1, node = node.parentElement) {
      const candidateText = norm(node.textContent);

      if (
        candidateText.includes("selected_asset_only") &&
        candidateText.includes("no portfolio aggregation")
      ) {
        const rect = node.getBoundingClientRect();

        // Hide only the small scope badge/card, never the whole report page.
        if (
          rect.width >= 120 &&
          rect.width <= 420 &&
          rect.height >= 40 &&
          rect.height <= 180
        ) {
          node.style.setProperty("display", "none", "important");
          node.dataset.simrasHiddenReportScope = "true";
          break;
        }
      }
    }
  }
}

function applyUltraMinimalReportsUi() {
  hideExportButtons();
  hideScopeCard();
}

export function ReportsUltraMinimalPruner() {
  useEffect(() => {
    let frame = 0;

    const run = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(applyUltraMinimalReportsUi);
    };

    run();

    const observer = new MutationObserver(run);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, []);

  return null;
}
