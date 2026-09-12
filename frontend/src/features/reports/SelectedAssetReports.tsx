import { useEffect as useReportsEffect, useState as useReportsState } from "react";
import { api as reportsApi } from "../../services/simrasTwinApi";
import DamOperationalForecastPanel from "./DamOperationalForecastPanel";
import DamBarrageOfficialEvidence from "./DamBarrageOfficialEvidence";
import BridgeEngineeringEvidence from "./BridgeEngineeringEvidence";
import { AssessmentDocumentView } from "./AssessmentDocumentView";
type UnknownRecord = Record<string, unknown>;

interface SelectedAssetReportsProps {
  selected?: unknown;
  twin?: unknown;
}


function isRecord(
  value: unknown,
): value is UnknownRecord {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}


function findDeep(
  root: unknown,
  names: string[],
): unknown {
  const wanted = new Set(
    names.map(
      (name) => name.toLowerCase(),
    ),
  );

  const visited = new Set<object>();

  const walk = (
    value: unknown,
  ): unknown => {
    if (
      value === null ||
      value === undefined
    ) {
      return undefined;
    }

    if (typeof value === "string") {
      const trimmed = value.trim();

      if (
        trimmed.startsWith("{") ||
        trimmed.startsWith("[")
      ) {
        try {
          return walk(
            JSON.parse(trimmed),
          );
        } catch {
          return undefined;
        }
      }

      return undefined;
    }

    if (Array.isArray(value)) {
      for (const child of value) {
        const result = walk(child);

        if (result !== undefined) {
          return result;
        }
      }

      return undefined;
    }

    if (isRecord(value)) {
      if (visited.has(value)) {
        return undefined;
      }

      visited.add(value);

      for (
        const [key, child]
        of Object.entries(value)
      ) {
        if (
          wanted.has(
            key.toLowerCase(),
          )
        ) {
          return child;
        }
      }

      for (
        const child
        of Object.values(value)
      ) {
        const result = walk(child);

        if (result !== undefined) {
          return result;
        }
      }
    }

    return undefined;
  };

  return walk(root);
}


function textValue(
  root: unknown,
  names: string[],
): string | undefined {
  const value = findDeep(
    root,
    names,
  );

  if (
    value === null ||
    value === undefined
  ) {
    return undefined;
  }

  const text = String(value).trim();

  if (
    !text ||
    text.toLowerCase() === "null" ||
    text.toLowerCase() === "undefined"
  ) {
    return undefined;
  }

  return text;
}


function numberValue(
  root: unknown,
  names: string[],
): number | undefined {
  const value = findDeep(
    root,
    names,
  );

  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return undefined;
  }

  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : undefined;
}


function display(
  value: string | number | undefined,
  suffix = "",
): string {
  if (
    value === undefined ||
    value === ""
  ) {
    return "UNKNOWN";
  }

  if (typeof value === "number") {
    return `${value.toLocaleString()}${suffix}`;
  }

  return `${value}${suffix}`;
}


function normalizeReportCardStatus(
  value: unknown,
):
  | "WITHHELD"
  | "VALIDATED ML"
  | "ENGINEERING ESTIMATE"
  | "EXPERIMENTAL"
  | "RESEARCH_TRANSFER" {

  if (typeof value !== "string") {
    return "WITHHELD";
  }

  const normalized = value
    .trim()
    .toUpperCase()
    .replaceAll("_", " ");

  if (normalized === "VALIDATED ML") {
    return "VALIDATED ML";
  }

  if (normalized === "ENGINEERING ESTIMATE") {
    return "ENGINEERING ESTIMATE";
  }

  if (normalized === "EXPERIMENTAL") {
    return "EXPERIMENTAL";
  }

  if (normalized === "RESEARCH TRANSFER") {
    return "RESEARCH_TRANSFER";
  }

  if (normalized === "WITHHELD") {
    return "WITHHELD";
  }

  return "WITHHELD";
}


function ReportCard({
  title,
  value,
  status,
  explanation,
}: {
  title: string;
  value: string;
  status:
    | "WITHHELD"
    | "VALIDATED ML"
    | "ENGINEERING ESTIMATE"
    | "EXPERIMENTAL"
    | "RESEARCH_TRANSFER";
  explanation: string;
}) {
  const statusColor =
    status === "VALIDATED ML"
      ? "#34d399"
      : status === "ENGINEERING ESTIMATE"
        ? "#60a5fa"
        : (status === "EXPERIMENTAL" || status === "RESEARCH_TRANSFER")
          ? "#fbbf24"
          : "#f87171";

  return (
    <article
      style={{
        minHeight: 155,
        border:
          "1px solid rgba(148,163,184,.18)",
        borderRadius: 12,
        padding: 18,
        background:
          "rgba(10,20,32,.76)",
      }}
    >
      <div
        style={{
          fontSize: 12,
          color: "#94a3b8",
          fontWeight: 700,
          letterSpacing: ".06em",
          textTransform: "uppercase",
        }}
      >
        {title}
      </div>

      <div
        style={{
          marginTop: 12,
          fontSize: 27,
          fontWeight: 800,
          color: "#f8fafc",
        }}
      >
        {value}
      </div>

      <div
        style={{
          display: "inline-block",
          marginTop: 11,
          padding: "4px 8px",
          borderRadius: 999,
          fontSize: 10,
          fontWeight: 800,
          letterSpacing: ".05em",
          color: statusColor,
          border:
            `1px solid ${statusColor}`,
        }}
      >
        {status}
      </div>

      <div
        style={{
          marginTop: 9,
          color: "#94a3b8",
          fontSize: 11,
          lineHeight: 1.45,
        }}
      >
        {explanation}
      </div>
    </article>
  );
}


function Specification({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns:
          "minmax(120px, 0.7fr) 1fr",
        gap: 16,
        padding: "10px 0",
        borderBottom:
          "1px solid rgba(148,163,184,.10)",
      }}
    >
      <span
        style={{
          color: "#94a3b8",
          fontSize: 12,
        }}
      >
        {label}
      </span>

      <strong
        style={{
          color: "#e2e8f0",
          fontSize: 12,
        }}
      >
        {value}
      </strong>
    </div>
  );
}


function stringListValue(
  root: unknown,
  names: string[],
): string[] {

  const value =
    findDeep(
      root,
      names,
    );

  if (
    value === null ||
    value === undefined
  ) {
    return [];
  }


  if (Array.isArray(value)) {

    return value
      .map((item) => {

        if (
          typeof item === "string" ||
          typeof item === "number"
        ) {
          return String(item).trim();
        }

        if (
          typeof item === "object" &&
          item !== null
        ) {
          try {
            return JSON.stringify(item);
          } catch {
            return "";
          }
        }

        return "";
      })
      .filter(
        (item) =>
          item.length > 0,
      );
  }


  if (
    typeof value === "object" &&
    value !== null
  ) {

    return Object.entries(
      value as Record<string, unknown>,
    )
      .map(
        ([key, item]) => {

          if (
            item === null ||
            item === undefined
          ) {
            return "";
          }

          if (
            typeof item === "object"
          ) {
            try {
              return `${key}: ${JSON.stringify(item)}`;
            } catch {
              return "";
            }
          }

          return `${key}: ${String(item)}`;
        },
      )
      .filter(
        (item) =>
          item.length > 0,
      );
  }


  const text =
    String(value).trim();

  if (!text) {
    return [];
  }


  if (text.includes(",")) {

    return text
      .split(",")
      .map(
        (item) =>
          item.trim(),
      )
      .filter(Boolean);
  }


  return [text];
}



export function SelectedAssetReports({
  selected,
  twin,
}: SelectedAssetReportsProps) {
  const source = {
    selected,
    twin,
  };


  // =========================================================
  // IDENTITY
  // =========================================================

  const assetName =
    textValue(
      selected,
      [
        "name",
        "asset_name",
      ],
    ) ?? "Selected infrastructure asset";


  const assetCode =
    textValue(
      selected,
      [
        "asset_code",
        "code",
      ],
    ) ?? "UNKNOWN";


  const assetType =
    textValue(
      selected,
      [
        "asset_type",
        "type",
      ],
    ) ?? "UNKNOWN";


  const district =
    textValue(
      selected,
      [
        "district",
      ],
    ) ?? "UNKNOWN";


  const identityStatus =
    textValue(
      selected,
      [
        "identity_status",
      ],
    ) ?? "UNKNOWN";


  // =========================================================
  // ENGINEERING DIMENSIONS
  // =========================================================

  const lengthM =
    numberValue(
      source,
      [
        "length_m",
        "total_length_m",
        "bridge_length_m",
        "verified_length_m",
      ],
    );


  const widthM =
    numberValue(
      source,
      [
        "width_m",
        "deck_width_m",
        "verified_width_m",
      ],
    );


  const heightM =
    numberValue(
      source,
      [
        "height_m",
        "structural_height_m",
        "dam_height_m",
      ],
    );


  const completionYear =
    numberValue(
      source,
      [
        "completion_year",
        "year_built",
        "built_year",
        "commissioned_year",
      ],
    );


  const spans =
    numberValue(
      source,
      [
        "span_count",
        "number_of_spans",
        "spans",
      ],
    );


  const piers =
    numberValue(
      source,
      [
        "pier_count",
        "number_of_piers",
        "piers",
      ],
    );


  const gates =
    numberValue(
      source,
      [
        "gate_count",
        "number_of_gates",
        "gates",
      ],
    );


  const capacity =
    numberValue(
      source,
      [
        "capacity",
        "storage_capacity",
        "gross_storage_capacity",
        "reservoir_capacity",
      ],
    );


  const geometrySource =
    textValue(
      source,
      [
        "geometry_source",
        "source_geometry",
      ],
    ) ?? "UNKNOWN";


  // =========================================================
  // IMPORTANT:
  //
  // Morning DB audit confirmed:
  //
  // Health remains withheld without validated labels.
  // Risk may contain selective RESEARCH_TRANSFER rows.
  // RUL remains experimental / withheld.
  // inspections        = 1
  //
  // Therefore the production report MUST NOT promote
  // numeric health/risk/RUL values as validated predictions.
  // =========================================================



  const reportAssetType =
    assetType.toLowerCase();

  // ==========================================================
  // ML6D_STORED_RISK_BEGIN
  //
  // Stored bridge Risk integration.
  //
  // RESEARCH_TRANSFER is reportable decision support.
  // It is NOT Andhra Pradesh ground-truth validation.
  // ==========================================================

  type StoredRiskPrediction = {
    available: boolean;
    asset_code: string;
    asset_name?: string | null;
    asset_type?: string | null;
    risk_score: number | null;
    risk_level: string | null;
    confidence_score: number | null;
    status: string;
    model_version: string | null;
    feature_version: string | null;
    prediction_time: string | null;
    factors: Record<string, unknown> | null;
    interpretation: string;
  };

  const reportAssetCodeForRisk =
    textValue(
      source,
      [
        "asset_code",
        "assetCode",
        "code",
      ],
    );

  const [
    storedRiskPrediction,
    setStoredRiskPrediction,
  ] = useReportsState<
    StoredRiskPrediction | null
  >(null);

  useReportsEffect(
    () => {
      let cancelled = false;

      setStoredRiskPrediction(
        null,
      );

      if (
        reportAssetType !== "bridge" ||
        !reportAssetCodeForRisk
      ) {
        return () => {
          cancelled = true;
        };
      }

      reportsApi
        .riskPrediction(
          reportAssetCodeForRisk,
        )
        .then(
          (prediction) => {
            if (!cancelled) {
              setStoredRiskPrediction(
                prediction,
              );
            }
          },
        )
        .catch(
          () => {
            if (!cancelled) {
              setStoredRiskPrediction(
                null,
              );
            }
          },
        );

      return () => {
        cancelled = true;
      };
    },
    [
      reportAssetCodeForRisk,
      reportAssetType,
    ],
  );

  const storedRiskAvailable =
    storedRiskPrediction?.available ===
      true &&
    storedRiskPrediction.risk_score !==
      null &&
    (
      storedRiskPrediction.status ===
        "RESEARCH_TRANSFER" ||
      storedRiskPrediction.status ===
        "VALIDATED_ML"
    );

  const storedRiskScore =
    storedRiskAvailable
      ? Number(
          storedRiskPrediction
            ?.risk_score,
        )
      : undefined;

  const storedRiskLevel =
    storedRiskAvailable
      ? (
          storedRiskPrediction
            ?.risk_level ??
          "WITHHELD"
        )
      : "WITHHELD";

  const storedRiskFactorPayload =
    storedRiskPrediction?.factors &&
    typeof storedRiskPrediction
      .factors === "object"
      ? storedRiskPrediction.factors
      : undefined;

  const storedRiskFactors =
    Array.isArray(
      storedRiskFactorPayload?.[
        "why_predicted"
      ],
    )
      ? (
          storedRiskFactorPayload?.[
            "why_predicted"
          ] as unknown[]
        )
          .map(
            (item) => {
              if (
                typeof item ===
                "string"
              ) {
                return item;
              }

              if (
                !item ||
                typeof item !==
                  "object"
              ) {
                return "";
              }

              const row =
                item as Record<
                  string,
                  unknown
                >;

              const feature =
                String(
                  row[
                    "feature"
                  ] ?? "feature",
                ).replace(
                  /_/g,
                  " ",
                );

              const direction =
                String(
                  row[
                    "direction"
                  ] ??
                  "LIMITED_EFFECT",
                )
                  .replace(
                    /_/g,
                    " ",
                  )
                  .toLowerCase();

              const rawEffect =
                row[
                  "effect_on_probability"
                ];

              const effect =
                typeof rawEffect ===
                  "number"
                  ? rawEffect
                  : Number(
                      rawEffect,
                    );

              if (
                Number.isFinite(
                  effect,
                )
              ) {

                const points =
                  effect * 100;

                return (
                  `${feature}: ` +
                  `${direction}; ` +
                  `probability effect ` +
                  `${points >= 0 ? "+" : ""}` +
                  `${points.toFixed(3)} ` +
                  `percentage points relative ` +
                  `to the model reference.`
                );
              }

              return (
                `${feature}: ` +
                direction
              );
            },
          )
          .filter(
            (
              item,
            ): item is string =>
              item.length > 0,
          )
      : [];

  const storedRiskRecommendations =
    Array.isArray(
      storedRiskFactorPayload?.[
        "recommendations"
      ],
    )
      ? (
          storedRiskFactorPayload?.[
            "recommendations"
          ] as unknown[]
        )
          .filter(
            (
              item,
            ): item is string =>
              typeof item ===
              "string",
          )
      : [];

  const reportSource = {
    ...source,

    ...(storedRiskAvailable
      ? {
          risk_prediction_status:
            storedRiskPrediction
              ?.status,

          risk_model_status:
            storedRiskPrediction
              ?.status,

          risk_validation_status:
            storedRiskPrediction
              ?.status,

          risk_score:
            storedRiskScore,

          structural_risk_score:
            storedRiskScore,

          predicted_risk_score:
            storedRiskScore,

          risk_level:
            storedRiskLevel,

          structural_risk_level:
            storedRiskLevel,

          prediction_factors:
            storedRiskFactors,

          risk_factors:
            storedRiskFactors,
        }
      : {}),
  };

  // ML6D_STORED_RISK_END



  // =========================================================
  // DAM / BARRAGE ENGINEERING + HYDROLOGY
  // =========================================================

  const riverName =
    textValue(
      reportSource,
      [
        "river_name",
        "river",
        "watercourse",
      ],
    );


  const crestLengthM =
    numberValue(
      reportSource,
      [
        "crest_length_m",
        "dam_length_m",
        "barrage_length_m",
        "structure_length_m",
      ],
    );


  const grossStorageMcm =
    numberValue(
      reportSource,
      [
        "gross_storage_capacity_mcm",
        "gross_capacity_mcm",
        "gross_storage_mcm",
        "storage_mcm",
      ],
    );


  const liveStorageMcm =
    numberValue(
      reportSource,
      [
        "live_storage_capacity_mcm",
        "live_capacity_mcm",
        "live_storage_mcm",
      ],
    );


  const waterLevelM =
    numberValue(
      reportSource,
      [
        "water_level_m",
        "reservoir_level_m",
        "current_level_m",
      ],
    );


  const dischargeCumecs =
    numberValue(
      reportSource,
      [
        "discharge_cumecs",
        "current_discharge_cumecs",
        "flow_cumecs",
      ],
    );


  const designFloodCumecs =
    numberValue(
      reportSource,
      [
        "design_flood_cumecs",
        "design_discharge_cumecs",
      ],
    );


  const spillwayCapacityCumecs =
    numberValue(
      reportSource,
      [
        "spillway_capacity_cumecs",
        "spill_capacity_cumecs",
      ],
    );


  // =========================================================
  // BRIDGE ENGINEERING
  // =========================================================

  const bridgeType =
    textValue(
      reportSource,
      [
        "bridge_type",
        "bridge_subtype",
        "structure_type",
        "subtype",
      ],
    );


  const bridgeMaterial =
    textValue(
      reportSource,
      [
        "bridge_material",
        "superstructure_material",
        "construction_material",
        "material",
      ],
    );


  const alignmentSource =
    textValue(
      reportSource,
      [
        "alignment_source",
        "geometry_source",
        "source_geometry",
      ],
    );


  // =========================================================
  // AIRPORT ENGINEERING
  // =========================================================

  const icaoCode =
    textValue(
      reportSource,
      [
        "icao_code",
        "icao",
      ],
    );


  const iataCode =
    textValue(
      reportSource,
      [
        "iata_code",
        "iata",
      ],
    );


  const runwayLengthM =
    numberValue(
      reportSource,
      [
        "runway_length_m",
        "runway_length",
      ],
    );


  const runwayWidthM =
    numberValue(
      reportSource,
      [
        "runway_width_m",
        "runway_width",
      ],
    );


  const runwaySurface =
    textValue(
      reportSource,
      [
        "runway_surface",
        "runway_pavement",
        "pavement_type",
        "surface",
      ],
    );


  const pavementStrength =
    textValue(
      reportSource,
      [
        "pavement_strength",
        "pavement_classification_number",
        "pcn",
      ],
    );


  const airportElevationM =
    numberValue(
      reportSource,
      [
        "airport_elevation_m",
        "aerodrome_elevation_m",
        "elevation_m",
      ],
    );


  // =========================================================
  // TEMPLE ENGINEERING
  // =========================================================

  const templeAreaM2 =
    numberValue(
      reportSource,
      [
        "site_area_m2",
        "built_area_m2",
        "land_area_m2",
        "area_m2",
      ],
    );


  const templePeriod =
    textValue(
      reportSource,
      [
        "construction_period",
        "historical_period",
        "built_period",
        "era",
      ],
    );


  const templeMaterial =
    textValue(
      reportSource,
      [
        "primary_material",
        "construction_material",
        "material",
      ],
    );


  // =========================================================
  // EVIDENCE / PROVENANCE
  // =========================================================

  const reportSourceName =
    textValue(
      reportSource,
      [
        "source_name",
        "data_source_name",
        "authority",
      ],
    );


  const reportEvidenceClass =
    textValue(
      reportSource,
      [
        "evidence_class",
        "evidence_type",
        "source_class",
      ],
    );


  const reportSourceDate =
    textValue(
      reportSource,
      [
        "source_date",
        "observation_date",
        "measurement_date",
        "observed_at",
      ],
    );


  const reportQuality =
    textValue(
      reportSource,
      [
        "quality_flag",
        "quality_status",
        "data_quality",
      ],
    );



  // =========================================================
  // PREDICTION EXPLANATION / RISK ASSESSMENT
  //
  // Validated predictions and explicitly gated
  // RESEARCH_TRANSFER Risk predictions may be shown.
  // Their transfer status must remain visible.
  // =========================================================

  const riskPredictionStatus =
    textValue(
      reportSource,
      [
        "risk_prediction_status",
        "risk_model_status",
        "risk_validation_status",
      ],
    );


  const healthPredictionStatus =
    textValue(
      reportSource,
      [
        "health_prediction_status",
        "health_model_status",
        "health_validation_status",
      ],
    );


  const reportedRiskScore =
    numberValue(
      reportSource,
      [
        "structural_risk_score",
        "validated_risk_score",
      ],
    );


  const reportedRiskLevel =
    textValue(
      reportSource,
      [
        "structural_risk_level",
        "validated_risk_level",
      ],
    );


  const predictionFactors =
    stringListValue(
      reportSource,
      [
        "prediction_factors",
        "risk_factors",
        "contributing_factors",
        "feature_contributions",
        "prediction_explanation",
      ],
    );


  const normalizedRiskStatus =
    (
      riskPredictionStatus ??
      ""
    ).toUpperCase();


  const structuralRiskValidated =
    normalizedRiskStatus.includes(
      "VALIDATED",
    ) ||
    normalizedRiskStatus.includes(
      "RESEARCH_TRANSFER",
    );


  const normalizedHealthStatus =
    (
      healthPredictionStatus ??
      ""
    ).toUpperCase();


  const structuralHealthValidated =
    normalizedHealthStatus.includes(
      "VALIDATED",
    );


  const recommendations: string[] = [];

  for (
    const recommendation
    of storedRiskRecommendations
  ) {
    if (
      !recommendations.includes(
        recommendation,
      )
    ) {
      recommendations.push(
        recommendation,
      );
    }
  }



  if (
    !structuralHealthValidated ||
    !structuralRiskValidated
  ) {

    recommendations.push(
      "Obtain or ingest a current structural inspection before using Health or structural Risk for engineering decisions.",
    );
  }


  if (reportAssetType === "bridge") {

    recommendations.push(
      "Verify deck, bearings, joints, piers, abutments and visible deterioration through a field bridge inspection.",
    );

    if (
      widthM === undefined ||
      spans === undefined ||
      piers === undefined
    ) {
      recommendations.push(
        "Complete missing bridge inventory dimensions and support counts using authoritative engineering records or field verification.",
      );
    }
  }


  if (
    reportAssetType === "dam" ||
    reportAssetType === "barrage"
  ) {

    recommendations.push(
      "Continue monitoring reservoir level, discharge and hydrology trends independently from structural condition assessment.",
    );

    recommendations.push(
      "Use an engineering safety inspection before interpreting hydrology anomalies as evidence of structural deterioration.",
    );
  }


  if (reportAssetType === "airport") {

    recommendations.push(
      "Obtain recent pavement condition or PCI inspection evidence before assigning runway or pavement Health and Remaining Useful Life.",
    );
  }


  if (reportAssetType === "temple") {

    recommendations.push(
      "Conduct a documented structural condition survey covering cracks, settlement, moisture deterioration and material condition.",
    );
  }


  recommendations.push(
    "Preserve source authority, observation date and evidence quality with every value included in future assessments.",
  );


  const experimentalRul =
    numberValue(
      reportSource,
      [
        "remaining_useful_life",
        "rul",
        "rul_years",
      ],
    );



  // ============================================================
  // CANONICAL SELECTED-ASSET ML DECISION-SUPPORT OUTPUT
  //
  // These values come from the current backend selected-asset
  // report/twin response. They are model-generated decision
  // support values, not government structural ratings.
  // ============================================================

  const predictionRoot =
    reportSource as any;

  const structuralDecision =
    predictionRoot?.decision_support
      ?.prediction
      ?.structural ??
    predictionRoot?.twin?.ai ??
    {};

  const reportHealthScore =
    Number.isFinite(
      Number(
        structuralDecision?.health_score,
      ),
    )
      ? Number(
          structuralDecision.health_score,
        )
      : undefined;

  const reportRiskScore =
    Number.isFinite(
      Number(
        structuralDecision?.risk_score,
      ),
    )
      ? Number(
          structuralDecision.risk_score,
        )
      : undefined;

  const reportRiskLevel =
    typeof structuralDecision?.risk_level ===
    "string"
      ? structuralDecision.risk_level
      : undefined;

  const confidenceCandidate =
    predictionRoot?.decision_support
      ?.prediction
      ?.prediction_confidence ??
    structuralDecision?.confidence;

  const reportPredictionConfidence =
    Number.isFinite(
      Number(confidenceCandidate),
    )
      ? Number(confidenceCandidate)
      : undefined;

  const reportPredictionConfidencePct =
    reportPredictionConfidence === undefined
      ? undefined
      : reportPredictionConfidence <= 1
        ? reportPredictionConfidence * 100
        : reportPredictionConfidence;

  const reportPredictionStage =
    predictionRoot?.decision_support
      ?.model
      ?.stage ??
    structuralDecision?.status ??
    "RESEARCH_TRANSFER";

  const reportPredictionMethod =
    predictionRoot?.decision_support
      ?.model
      ?.prediction_method ??
    structuralDecision?.prediction_method ??
    "ML";

  const reportModelVersion =
    predictionRoot?.decision_support
      ?.model
      ?.model_version ??
    structuralDecision?.model_version ??
    "NOT_AVAILABLE";

  const reportStructuralAvailable =
    structuralDecision?.available === true ||
    (
      reportHealthScore !== undefined &&
      reportRiskScore !== undefined
    );
  
  

return (
    <>
      {/* SIMRAS_ASSESSMENT_DOCUMENT_REPLACE_V3 */}
      <AssessmentDocumentView
        assetCode={assetCode}
      />
    </>
  );
}

export default SelectedAssetReports;


