import { jsPDF } from "jspdf";

type UnknownRecord = Record<string, any>;

export interface ReferencePdfExportInput {
  assetCode: string;
  asset?: UnknownRecord | null;
  reportData?: UnknownRecord | null;
}

type FlatEntry = { path: string; key: string; value: any };
type Point = { label: string; value: number };
type MetricSpec = {
  label: string;
  aliases: string[];
  unit: string;
  chartTitle: string;
};

const METRICS: MetricSpec[] = [
  {
    label: "Rainfall 1 h",
    aliases: ["rainfall_1h", "rainfall1h", "rainfall_mm_hr", "precipitation_1h"],
    unit: "mm",
    chartTitle: "Rainfall 1 h",
  },
  {
    label: "Rainfall 24 h",
    aliases: ["rainfall_24h", "rainfall24h", "precipitation_24h"],
    unit: "mm",
    chartTitle: "Rainfall 24 h",
  },
  {
    label: "Rainfall 7 d",
    aliases: ["rainfall_7d", "rainfall7d", "precipitation_7d"],
    unit: "mm",
    chartTitle: "Rainfall 7 d",
  },
  {
    label: "Relative humidity",
    aliases: ["relative_humidity_2m", "relative_humidity", "humidity_pct", "humidity"],
    unit: "%",
    chartTitle: "Relative humidity",
  },
  {
    label: "Temperature",
    aliases: ["temperature_2m", "temperature_c", "temperature"],
    unit: "degC",
    chartTitle: "Temperature",
  },
  {
    label: "Wind speed",
    aliases: ["wind_speed_10m", "wind_speed_kmh", "wind_speed", "windspeed"],
    unit: "m/s",
    chartTitle: "Wind speed",
  },
];

const normalize = (value: unknown) =>
  String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");

const clean = (value: unknown) =>
  String(value ?? "")
    .replace(/•/g, "•")
    .replace(/Ã¢â€ ’/g, "→")
    .replace(/Ã¢â€°¥/g, "≥")
    .replace(/Ã¢â€°¤/g, "≤")
    .replace(/Ã¢â‚¬â€œ/g, "–")
    .replace(/Ã¢â‚¬â€/g, "—")
    .replace(/Ã¢â‚¬â„¢/g, "'")
    .replace(/Ã‚/g, "")
    .replace(/\uFFFD/g, "")
    .trim();

const display = (value: any, fallback = "NOT AVAILABLE") => {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "number" && !Number.isFinite(value)) return fallback;
  if (typeof value === "object") {
    const preferred =
      value.value ??
      value.numeric_value ??
      value.current ??
      value.current_value ??
      value.result ??
      value.label;
    if (preferred !== undefined && preferred !== null) {
      const unit = value.unit ? ` ${clean(value.unit)}` : "";
      return `${clean(preferred)}${unit}`;
    }
    return fallback;
  }
  return clean(value) || fallback;
};

const num = (value: any): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const match = value.replace(/,/g, "").match(/-?\d+(?:\.\d+)?/);
    if (match) {
      const parsed = Number(match[0]);
      return Number.isFinite(parsed) ? parsed : null;
    }
  }
  if (value && typeof value === "object") {
    return num(value.numeric_value ?? value.value ?? value.current ?? value.current_value);
  }
  return null;
};

function flatten(value: any, path = "", out: FlatEntry[] = [], depth = 0): FlatEntry[] {
  if (depth > 9 || value === null || value === undefined) return out;
  if (Array.isArray(value)) {
    value.forEach((item, index) => flatten(item, `${path}[${index}]`, out, depth + 1));
    return out;
  }
  if (typeof value === "object") {
    Object.entries(value).forEach(([key, item]) => {
      const next = path ? `${path}.${key}` : key;
      if (item === null || item === undefined || typeof item !== "object") {
        out.push({ path: next, key, value: item });
      } else {
        flatten(item, next, out, depth + 1);
      }
    });
    return out;
  }
  out.push({ path, key: path.split(".").pop() ?? path, value });
  return out;
}

function findScalar(root: any, aliases: string[]): { value: any; path: string } | null {
  const wanted = aliases.map(normalize);
  const entries = flatten(root);
  const exact = entries.find((entry) => wanted.includes(normalize(entry.key)));
  if (exact) return { value: exact.value, path: exact.path };
  const fuzzy = entries.find((entry) => {
    const p = normalize(entry.path);
    return wanted.some((alias) => p.includes(alias));
  });
  return fuzzy ? { value: fuzzy.value, path: fuzzy.path } : null;
}

function collectArrays(value: any, path = "", out: { path: string; items: any[] }[] = [], depth = 0) {
  if (depth > 8 || value === null || value === undefined) return out;
  if (Array.isArray(value)) {
    out.push({ path, items: value });
    value.forEach((item, index) => {
      if (item && typeof item === "object") {
        collectArrays(item, `${path}[${index}]`, out, depth + 1);
      }
    });
    return out;
  }
  if (typeof value === "object") {
    Object.entries(value).forEach(([key, item]) => {
      collectArrays(item, path ? `${path}.${key}` : key, out, depth + 1);
    });
  }
  return out;
}

function dateLabel(item: UnknownRecord, index: number) {
  const raw =
    item.date ??
    item.timestamp ??
    item.time ??
    item.datetime ??
    item.observed_at ??
    item.updated_at ??
    item.generated_at;
  if (!raw) return String(index + 1);
  const d = new Date(raw);
  if (!Number.isNaN(d.getTime())) {
    return d.toISOString().slice(0, 10);
  }
  return clean(raw);
}

function findSeries(root: any, aliases: string[]): Point[] {
  const wanted = aliases.map(normalize);
  const arrays = collectArrays(root);

  for (const candidate of arrays) {
    const pathNorm = normalize(candidate.path);
    const pathMatches = wanted.some((alias) => pathNorm.includes(alias));
    const points: Point[] = [];

    candidate.items.forEach((item, index) => {
      if (typeof item === "number") {
        if (pathMatches && Number.isFinite(item)) {
          points.push({ label: String(index + 1), value: item });
        }
        return;
      }

      if (!item || typeof item !== "object") return;

      let found: number | null = null;
      for (const [key, value] of Object.entries(item)) {
        if (wanted.some((alias) => normalize(key).includes(alias))) {
          found = num(value);
          if (found !== null) break;
        }
      }

      if (found === null && pathMatches) {
        found = num(
          item.value ??
            item.current ??
            item.current_value ??
            item.measurement ??
            item.reading,
        );
      }

      if (found !== null) {
        points.push({ label: dateLabel(item, index), value: found });
      }
    });

    if (points.length >= 2) return points;
  }
  return [];
}

function findArrayByName(root: any, tokens: string[]): any[] {
  const wanted = tokens.map(normalize);
  const arrays = collectArrays(root);
  const match = arrays.find((candidate) => {
    const p = normalize(candidate.path);
    return wanted.some((token) => p.includes(token)) && candidate.items.length > 0;
  });
  return match?.items ?? [];
}

async function safeJson(url: string): Promise<any> {
  try {
    const response = await fetch(url);
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

async function loadWatermark(): Promise<string | null> {
  try {
    const response = await fetch("/ap-state-emblem.png", { cache: "no-store" });
    if (!response.ok) return null;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    try {
      const image = await new Promise<HTMLImageElement>((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = url;
      });

      const canvas = document.createElement("canvas");
      canvas.width = 1000;
      canvas.height = 1000;
      const ctx = canvas.getContext("2d");
      if (!ctx) return null;

      const scale = Math.min(820 / image.naturalWidth, 820 / image.naturalHeight);
      const width = image.naturalWidth * scale;
      const height = image.naturalHeight * scale;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.globalAlpha = 0.075;
      ctx.drawImage(
        image,
        (canvas.width - width) / 2,
        (canvas.height - height) / 2,
        width,
        height,
      );
      return canvas.toDataURL("image/png");
    } finally {
      URL.revokeObjectURL(url);
    }
  } catch {
    return null;
  }
}

function pick(root: any, aliases: string[], fallback: any = null) {
  return findScalar(root, aliases)?.value ?? fallback;
}

function titleize(value: string) {
  return clean(value)
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function engineeringRows(asset: UnknownRecord): string[][] {
  const dimensions = asset?.dimensions;
  if (!dimensions || typeof dimensions !== "object") return [];

  return Object.entries(dimensions).slice(0, 20).map(([key, raw]) => {
    if (raw && typeof raw === "object") {
      return [
        titleize(key),
        display(raw),
        display(raw.verification_status ?? raw.status, "NOT AVAILABLE"),
        display(raw.source_code ?? raw.source ?? raw.source_name, "NOT AVAILABLE"),
      ];
    }
    return [titleize(key), display(raw), "NOT AVAILABLE", "NOT AVAILABLE"];
  });
}

function evidenceRows(report: UnknownRecord): string[][] {
  const entries = flatten(report);
  const rows: string[][] = [];
  const seen = new Set<string>();

  for (const entry of entries) {
    const path = normalize(entry.path);
    if (
      !(
        path.includes("evidence") ||
        path.includes("source") ||
        path.includes("threshold") ||
        path.includes("compliance") ||
        path.includes("provenance") ||
        path.includes("verification")
      )
    ) {
      continue;
    }
    const value = display(entry.value, "");
    if (!value) continue;
    const key = `${entry.path}:${value}`;
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push([clean(entry.path), value]);
    if (rows.length >= 18) break;
  }
  return rows;
}

function factorRows(asset: UnknownRecord, report: UnknownRecord): string[][] {
  const specs = [
    ["Age", ["age", "current_age_years", "asset_age_years"]],
    ["Structural condition rating", ["structural_condition_rating", "condition_rating"]],
    ["Material", ["material", "construction_material"]],
    ["Span count", ["span_count", "number_of_spans"]],
    ["Pillar / pier count", ["pillar_count", "pier_count", "number_of_pillars"]],
    ["Structure length", ["structure_length", "length_m", "main_length_m", "total_length_m"]],
    ["Built year", ["built_year", "construction_year", "construction_completion_year"]],
  ] as const;

  const combined = { asset, report };
  const rows: string[][] = [];
  for (const [label, aliases] of specs) {
    const hit = findScalar(combined, [...aliases]);
    if (!hit) continue;
    rows.push([
      label,
      display(hit.value),
      "Stored reference only",
      "Model contribution not stored; no attribution inferred.",
    ]);
  }
  return rows;
}

function recommendationLines(report: UnknownRecord): string[] {
  const items = findArrayByName(report, ["recommendation", "recommendedaction", "decision_support"]);
  if (items.length) {
    return items.slice(0, 10).map((item) => {
      if (typeof item === "string") return clean(item);
      return clean(
        item.title ??
          item.recommendation ??
          item.action ??
          item.reason ??
          item.description ??
          JSON.stringify(item),
      );
    });
  }
  const scalar = findScalar(report, ["recommendation", "recommended_action", "recommended_actions"]);
  return scalar ? [display(scalar.value)] : [];
}

function operationalMetricForType(assetType: string): MetricSpec[] {
  const t = assetType.toUpperCase();
  if (t.includes("BRIDGE") || t.includes("ROAD")) {
    return [
      {
        label: "Traffic load",
        aliases: ["traffic_load_pcu", "traffic_load", "aadt", "vehicle_count", "traffic"],
        unit: "PCU / vehicles",
        chartTitle: "Traffic load",
      },
    ];
  }
  if (t.includes("AIRPORT")) {
    return [
      {
        label: "Aircraft movements / operational load",
        aliases: ["aircraft_movements", "flight_movements", "operational_load", "pavement_load"],
        unit: "movements / load",
        chartTitle: "Airport operational load",
      },
    ];
  }
  if (t.includes("DAM") || t.includes("BARRAGE")) {
    return [
      {
        label: "Water level",
        aliases: ["water_level", "reservoir_level", "river_level", "level_m"],
        unit: "m",
        chartTitle: "Water level",
      },
      {
        label: "Storage",
        aliases: ["storage", "reservoir_storage", "storage_mcm"],
        unit: "MCM",
        chartTitle: "Reservoir storage",
      },
      {
        label: "Discharge / flow",
        aliases: ["discharge", "flow_rate", "water_flow", "discharge_cumecs"],
        unit: "cumecs",
        chartTitle: "Discharge / flow",
      },
    ];
  }
  if (t.includes("TEMPLE")) {
    return [
      {
        label: "Footfall",
        aliases: ["footfall", "visitor_count", "pilgrim_count", "visitors"],
        unit: "visitors",
        chartTitle: "Visitor footfall",
      },
    ];
  }
  return [];
}

export async function exportSimrasReferencePdf(input: ReferencePdfExportInput) {
  const assetCode = input.assetCode;
  const encoded = encodeURIComponent(assetCode);

  const [freshReport, fullAsset, telemetry, inspectionsRaw, maintenanceRaw] =
    await Promise.all([
      safeJson(`/api/v1/assets/${encoded}/reports/real`),
      safeJson(`/api/v1/assets/${encoded}`),
      safeJson(`/api/v1/assets/${encoded}/telemetry`),
      safeJson(`/api/v1/inspections?asset_code=${encoded}`),
      safeJson(`/api/v1/maintenance?asset_code=${encoded}`),
    ]);

  const asset: UnknownRecord = fullAsset ?? input.asset ?? {};
  const report: UnknownRecord = freshReport ?? input.reportData ?? {};
  const inspections: any[] = Array.isArray(inspectionsRaw)
    ? inspectionsRaw
    : inspectionsRaw?.items ?? [];
  const maintenance: any[] = Array.isArray(maintenanceRaw)
    ? maintenanceRaw
    : maintenanceRaw?.items ?? [];

  const combined = { asset, report, telemetry, inspections, maintenance };
  const watermark = await loadWatermark();

  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
    compress: true,
  });

  const PAGE_W = doc.internal.pageSize.getWidth();
  const PAGE_H = doc.internal.pageSize.getHeight();
  const M = 14;
  const CONTENT_W = PAGE_W - M * 2;
  const BOTTOM = PAGE_H - 14;
  let y = 16;

  const addWatermark = () => {
    if (watermark) {
      const size = 120;
      doc.addImage(
        watermark,
        "PNG",
        (PAGE_W - size) / 2,
        (PAGE_H - size) / 2,
        size,
        size,
        undefined,
        "FAST",
      );
    }
  };

  const pageHeader = () => {
    addWatermark();
    doc.setTextColor(15, 65, 85);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.text("SIMRAS • Smart Infrastructure Monitoring & Risk Assistance System", M, 9);
    doc.setDrawColor(190, 205, 215);
    doc.line(M, 11, PAGE_W - M, 11);
  };

  const newPage = () => {
    doc.addPage();
    y = 16;
    pageHeader();
  };

  const ensure = (height: number) => {
    if (y + height > BOTTOM) newPage();
  };

  const section = (title: string) => {
    ensure(12);
    doc.setFillColor(10, 92, 112);
    doc.rect(M, y, CONTENT_W, 7, "F");
    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.text(clean(title), M + 2, y + 4.8);
    y += 10;
  };

  const paragraph = (text: string, fontSize = 8.5) => {
    const lines = doc.splitTextToSize(clean(text), CONTENT_W);
    const h = lines.length * 4 + 1;
    ensure(h);
    doc.setTextColor(35, 45, 55);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(fontSize);
    doc.text(lines, M, y);
    y += h;
  };

  const kvTable = (rows: string[][], widths?: number[]) => {
    if (!rows.length) {
      paragraph("DATA NOT AVAILABLE");
      return;
    }
    const cols = rows[0].length;
    const colWidths =
      widths && widths.length === cols
        ? widths
        : Array(cols).fill(CONTENT_W / cols);

    const drawRow = (row: string[], header = false) => {
      const cellLines = row.map((cell, index) =>
        doc.splitTextToSize(clean(cell), Math.max(colWidths[index] - 3, 8)),
      );
      const maxLines = Math.max(...cellLines.map((lines) => lines.length), 1);
      const rowH = Math.max(6.2, maxLines * 3.5 + 2.5);
      ensure(rowH);

      let x = M;
      row.forEach((_, index) => {
        if (header) doc.setFillColor(225, 239, 244);
        else doc.setFillColor(255, 255, 255);
        doc.setDrawColor(175, 195, 205);
        doc.rect(x, y, colWidths[index], rowH, "FD");
        doc.setTextColor(25, 35, 45);
        doc.setFont("helvetica", header ? "bold" : "normal");
        doc.setFontSize(header ? 7.6 : 7.2);
        doc.text(cellLines[index], x + 1.5, y + 3.8);
        x += colWidths[index];
      });
      y += rowH;
    };

    rows.forEach((row, index) => drawRow(row, index === 0));
    y += 3;
  };

  const lineChart = (title: string, points: Point[], unit: string) => {
    ensure(64);
    doc.setTextColor(25, 35, 45);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.text(clean(title), PAGE_W / 2, y + 2, { align: "center" });
    y += 7;

    if (points.length < 2) {
      doc.setFont("helvetica", "italic");
      doc.setFontSize(8);
      doc.text("INSUFFICIENT HISTORY — no trend graph generated.", M, y + 8);
      y += 18;
      return;
    }

    const chartX = M + 12;
    const chartY = y;
    const chartW = CONTENT_W - 18;
    const chartH = 45;
    const values = points.map((p) => p.value);
    let min = Math.min(...values);
    let max = Math.max(...values);
    if (min === max) {
      min -= 1;
      max += 1;
    }
    const pad = (max - min) * 0.08 || 1;
    min -= pad;
    max += pad;

    doc.setDrawColor(205, 215, 220);
    doc.setLineWidth(0.2);
    for (let i = 0; i <= 4; i++) {
      const gy = chartY + (chartH * i) / 4;
      doc.line(chartX, gy, chartX + chartW, gy);
    }

    doc.setDrawColor(70, 130, 170);
    doc.setLineWidth(0.7);
    const coords = points.map((p, i) => {
      const px = chartX + (chartW * i) / Math.max(points.length - 1, 1);
      const py = chartY + chartH - ((p.value - min) / (max - min)) * chartH;
      return { x: px, y: py };
    });
    coords.forEach((p, i) => {
      if (i > 0) doc.line(coords[i - 1].x, coords[i - 1].y, p.x, p.y);
      doc.setFillColor(45, 125, 175);
      doc.circle(p.x, p.y, 0.9, "F");
    });

    doc.setTextColor(80, 90, 100);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(6.8);
    doc.text(`${max.toFixed(2)} ${unit}`, M, chartY + 2);
    doc.text(`${min.toFixed(2)} ${unit}`, M, chartY + chartH);
    doc.text(clean(points[0].label), chartX, chartY + chartH + 5);
    doc.text(
      clean(points[Math.floor(points.length / 2)].label),
      chartX + chartW / 2,
      chartY + chartH + 5,
      { align: "center" },
    );
    doc.text(clean(points[points.length - 1].label), chartX + chartW, chartY + chartH + 5, {
      align: "right",
    });

    y = chartY + chartH + 10;
  };

  pageHeader();

  doc.setTextColor(15, 25, 35);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("SIMRAS AI-Powered Asset Health Assessment Report", M, y);
  y += 8;

  const reportId =
    display(
      pick(report, ["report_id", "reportid"]),
      `SIMRAS-${assetCode}-${new Date().toISOString().replace(/\D/g, "").slice(0, 14)}`,
    );
  const assetName = display(asset.name ?? asset.asset_name ?? pick(report, ["asset_name"]), assetCode);
  const assetType = display(asset.asset_type ?? asset.category ?? asset.type, "NOT AVAILABLE");
  const generated = new Date().toISOString();
  const status = display(asset.status ?? asset.current_status ?? pick(report, ["current_asset_status"]), "NOT AVAILABLE");

  kvTable(
    [
      ["Report field", "Value"],
      ["Report ID", reportId],
      ["Asset", `${assetCode} • ${assetName}`],
      ["Infrastructure type", assetType],
      ["District", display(asset.district)],
      ["Generated", generated],
      ["Current asset status", status],
    ],
    [48, CONTENT_W - 48],
  );

  section("Assessment Summary");

  const health =
    pick(report, ["health_score", "healthscore"]) ??
    asset.health_score;
  const risk =
    pick(report, ["risk_score", "riskscore"]) ??
    asset.risk_score;
  const rul =
    pick(report, ["rul_years", "predicted_rul_years", "remaining_useful_life", "rul"]);
  const confidence =
    pick(report, ["confidence", "confidence_pct", "model_confidence"]) ??
    asset.confidence;
  const riskLevel =
    pick(report, ["risk_level", "risklevel"]) ??
    asset.risk_level;

  kvTable(
    [
      ["Metric", "Value", "Status / interval"],
      ["Health score", health == null ? "WITHHELD" : `${display(health)}/100`, display(pick(report, ["health_status", "condition_class"]), "NOT AVAILABLE")],
      ["Risk", risk == null ? "WITHHELD" : `${display(risk)}/100`, display(riskLevel, "NOT AVAILABLE")],
      ["RUL", rul == null ? "WITHHELD" : `${display(rul)} years`, display(pick(report, ["rul_status", "rul_interval"]), "NOT AVAILABLE")],
      ["Confidence", confidence == null ? "WITHHELD" : display(confidence), display(pick(report, ["model_stage", "stage"]), "NOT AVAILABLE")],
    ],
    [45, 45, CONTENT_W - 90],
  );

  const rulSeries = findSeries(combined, ["rul", "remaining_useful_life", "predicted_rul_years"]);
  lineChart("RUL trend", rulSeries, "years");

  section("Why did the AI make this prediction?");
  const factors = factorRows(asset, report);
  kvTable(
    [["Factor", "Current value", "Expected / reference", "Impact"], ...(factors.length ? factors : [["Evidence", "NOT AVAILABLE", "NOT AVAILABLE", "No signed feature contribution stored."]])],
    [36, 36, 46, CONTENT_W - 118],
  );

  paragraph(
    "Prediction transparency rule: this report exposes stored model inputs, model metadata, evidence and observed histories. It does not invent SHAP values, regulatory thresholds or signed feature contributions when those records are absent.",
    7.8,
  );

  newPage();
  section("Engineering Profile");
  const eng = engineeringRows(asset);
  kvTable(
    [["Engineering field", "Value", "Verification", "Source"], ...(eng.length ? eng : [["Engineering dimensions", "DATA NOT AVAILABLE", "NOT AVAILABLE", "NOT AVAILABLE"]])],
    [45, 42, 40, CONTENT_W - 127],
  );

  section("Government Evidence & Standards");
  const evidence = evidenceRows(report);
  kvTable(
    [["Evidence / provenance path", "Stored value"], ...(evidence.length ? evidence : [["Evidence", "DATA NOT AVAILABLE"]])],
    [72, CONTENT_W - 72],
  );
  paragraph(
    "No regulatory threshold is inferred. Compliance is shown only when a verified threshold or standard is explicitly stored in the report evidence.",
    7.8,
  );

  section("Recommendations");
  const recommendations = recommendationLines(report);
  if (recommendations.length) {
    recommendations.forEach((item, index) => paragraph(`${index + 1}. ${item}`, 8));
  } else {
    paragraph("No evidence-backed recommendation is stored for this selected asset.");
  }

  section("Inspection Findings");
  if (inspections.length) {
    const rows = inspections.slice(0, 10).map((item) => [
      display(item.inspection_date ?? item.date),
      display(item.inspection_type ?? item.type),
      display(item.condition_rating ?? item.condition),
      display(item.findings ?? item.summary),
      display(item.status),
    ]);
    kvTable(
      [["Date", "Type", "Condition", "Findings", "Status"], ...rows],
      [25, 28, 28, 75, CONTENT_W - 156],
    );
  } else {
    paragraph("DATA NOT AVAILABLE");
  }

  section("Maintenance");
  if (maintenance.length) {
    const rows = maintenance.slice(0, 10).map((item) => [
      display(item.title ?? item.category),
      display(item.priority),
      display(item.status),
      display(item.scheduled_start ?? item.date),
      display(item.cost_inr_lakhs, "NOT AVAILABLE"),
    ]);
    kvTable(
      [["Work", "Priority", "Status", "Scheduled", "Cost (INR lakhs)"], ...rows],
      [64, 25, 28, 32, CONTENT_W - 149],
    );
  } else {
    paragraph("DATA NOT AVAILABLE");
  }

  newPage();
  section("Supporting Data");
  const supportRows: string[][] = [];
  const metricSeries: { spec: MetricSpec; points: Point[] }[] = [];

  for (const spec of METRICS) {
    const hit = findScalar(combined, spec.aliases);
    const points = findSeries(combined, spec.aliases);
    metricSeries.push({ spec, points });
    supportRows.push([
      spec.label,
      hit ? display(hit.value) : "DATA NOT AVAILABLE",
      spec.unit,
      points.length >= 2 ? "HISTORY AVAILABLE" : "INSUFFICIENT HISTORY",
      hit ? clean(hit.path) : "NOT AVAILABLE",
    ]);
  }

  const operationalSpecs = operationalMetricForType(assetType);
  for (const spec of operationalSpecs) {
    const hit = findScalar(combined, spec.aliases);
    const points = findSeries(combined, spec.aliases);
    metricSeries.push({ spec, points });
    supportRows.push([
      spec.label,
      hit ? display(hit.value) : "DATA NOT AVAILABLE",
      spec.unit,
      points.length >= 2 ? "HISTORY AVAILABLE" : "INSUFFICIENT HISTORY",
      hit ? clean(hit.path) : "NOT AVAILABLE",
    ]);
  }

  kvTable(
    [["Input", "Current", "Unit", "History", "Stored path / provenance"], ...supportRows],
    [42, 32, 24, 36, CONTENT_W - 134],
  );

  for (const item of metricSeries) {
    if (item.points.length >= 2) {
      lineChart(item.spec.chartTitle, item.points, item.spec.unit);
    }
  }

  if (!metricSeries.some((item) => item.points.length >= 2)) {
    paragraph(
      "No verified time-series history was found in the current report, telemetry or stored asset data. Graphs were not fabricated.",
      8.2,
    );
  }

  newPage();
  section("Prediction Transparency");
  const transparencyRows = [
    ["Prediction", display(pick(report, ["prediction", "health_status", "condition_class"]), "NOT AVAILABLE")],
    ["Confidence", confidence == null ? "WITHHELD" : display(confidence)],
    ["Model", display(pick(report, ["model_name", "model", "model_id"]), "NOT AVAILABLE")],
    ["Model version", display(pick(report, ["model_version", "version"]), "NOT AVAILABLE")],
    ["Prediction method", display(pick(report, ["prediction_method", "method"]), "NOT AVAILABLE")],
    ["Prediction generated", display(pick(report, ["prediction_generated", "generated_at", "predicted_at"]), "NOT AVAILABLE")],
    ["Data points used", display(pick(report, ["data_points_used", "samples_used"]), "NOT AVAILABLE")],
    ["Evidence records available", display(pick(report, ["evidence_records_available", "evidence_count"]), "NOT AVAILABLE")],
    ["Model stage", display(pick(report, ["model_stage", "stage"]), "NOT AVAILABLE")],
  ];
  kvTable([["Field", "Value"], ...transparencyRows], [58, CONTENT_W - 58]);

  section("Data Sources & Traceability");
  const traceRows = evidenceRows({ report, telemetry });
  kvTable(
    [["Traceability field", "Stored value"], ...(traceRows.length ? traceRows : [["Traceability", "DATA NOT AVAILABLE"]])],
    [72, CONTENT_W - 72],
  );

  paragraph(
    "Traceability boundary: populated values come from the selected asset record, current report JSON, telemetry, inspection and maintenance APIs. Missing thresholds, histories, failure probabilities and explainability contributions are not fabricated.",
    8,
  );

  // Ensure watermark is present on every page created before final save.
  const totalPages = doc.getNumberOfPages();
  for (let page = 1; page <= totalPages; page += 1) {
    doc.setPage(page);
    if (watermark) {
      const size = 120;
      doc.addImage(
        watermark,
        "PNG",
        (PAGE_W - size) / 2,
        (PAGE_H - size) / 2,
        size,
        size,
        undefined,
        "FAST",
      );
    }
    doc.setTextColor(100, 110, 120);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(6.5);
    doc.text(`SIMRAS • ${assetCode} • Page ${page} of ${totalPages}`, PAGE_W / 2, PAGE_H - 6, {
      align: "center",
    });
  }

  const safeName = clean(assetName)
    .replace(/[^A-Za-z0-9._-]+/g, "_")
    .replace(/^_+|_+$/g, "");

  doc.save(`${safeName || assetCode}_${assetCode}_SIMRAS_Asset_Health_Assessment.pdf`);
}