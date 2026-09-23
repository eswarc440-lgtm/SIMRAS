import { useEffect, useState } from "react";

import { damBarrageProfile } from "../../services/simrasTwinApi";


type EngineeringProfile = {
  cwc_pic?: string | null;
  cwc_name?: string | null;
  cwc_latitude?: number | null;
  cwc_longitude?: number | null;

  river?: string | null;
  river_basin?: string | null;
  nearest_city?: string | null;
  seismic_zone?: string | null;
  structure_type?: string | null;

  height_m?: number | null;
  length_m?: number | null;
  dam_volume_m3?: number | null;

  gross_storage_mcm?: number | null;
  effective_storage_mcm?: number | null;
  reservoir_area_m2?: number | null;

  spillway_capacity_cumecs?: number | null;

  purpose?: string | null;
  completion_year?: number | null;

  source_authority?: string | null;
  source_document?: string | null;
  source_url?: string | null;
  evidence_class?: string | null;
  quality_status?: string | null;

  match_method?: string | null;
  match_score?: number | null;
};


type HydrologyProfile = {
  level_station?: string | null;
  water_level_m?: number | null;
  water_level_time?: string | null;

  storage_station?: string | null;
  current_storage_mcm?: number | null;
  storage_time?: string | null;

  source_authority?: string | null;
  evidence_class?: string | null;

  level_match_method?: string | null;
  storage_match_method?: string | null;
};


type ProfileResponse = {
  available?: boolean;

  asset?: {
    asset_code?: string | null;
    name?: string | null;
    asset_type?: string | null;
    district?: string | null;
    latitude?: number | null;
    longitude?: number | null;
  } | null;

  engineering?: EngineeringProfile | null;
  hydrology?: HydrologyProfile | null;
};


type Props = {
  assetCode?: string | null;
};


const unavailable = "NOT AVAILABLE";


function textValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return unavailable;
  }

  return String(value);
}


function numericValue(
  value: number | null | undefined,
  unit = "",
  digits = 3,
): string {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(Number(value))
  ) {
    return unavailable;
  }

  const rendered = Number(value).toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });

  return unit ? `${rendered} ${unit}` : rendered;
}


function dateValue(value: string | null | undefined): string {
  if (!value) {
    return unavailable;
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}


function Row({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
            <div
              role="row"
              data-simras-report-table-row="true"
              style={{
                display: "grid",
                gridTemplateColumns:
                  "minmax(240px, 34%) minmax(0, 1fr)",
                width: "100%",
                minHeight: 44,
                borderBottom:
                  "1px solid rgba(148,163,184,.16)",
                background:
                  "rgba(2,12,21,.16)",
              }}
            >
              {/* SIMRAS_REPORT_TABLE_ROW_V3 */}

              <div
                role="cell"
                style={{
                  padding: "10px 14px",
                  color: "#94b8d3",
                  fontSize: 13,
                  fontWeight: 500,
                  lineHeight: 1.45,
                  borderRight:
                    "1px solid rgba(148,163,184,.12)",
                }}
              >
                {label}
              </div>

              <div
                role="cell"
                style={{
                  padding: "10px 14px",
                  color: "#f1f5f9",
                  fontSize: 13,
                  fontWeight: 700,
                  lineHeight: 1.45,
                  minWidth: 0,
                  overflowWrap: "anywhere",
                }}
              >
                {value}
              </div>
            </div>
          );
}


export default function DamBarrageOfficialEvidence({
  assetCode,
}: Props) {
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;

    if (!assetCode) {
      setProfile(null);

      return () => {
        active = false;
      };
    }

    setLoading(true);

    damBarrageProfile(assetCode)
      .then((response: ProfileResponse) => {
        if (active) {
          setProfile(response);
        }
      })
      .catch(() => {
        if (active) {
          setProfile(null);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [assetCode]);


  if (loading) {
    return (
      <div
        data-simras-dam-official-evidence="loading"
        className="rounded-xl border bg-card p-5"
      >
        <div className="text-sm text-muted-foreground">
          Loading official dam/barrage evidence...
        </div>
      </div>
    );
  }


  if (!profile?.available || !profile.engineering) {
    return null;
  }


  const e = profile.engineering;
  const h = profile.hydrology;


  return (
    <section
      data-simras-dam-official-evidence="ready"
      className="space-y-5 rounded-xl border bg-card p-5"
    >
      <div>
        <h3 className="text-lg font-semibold">
          Official Engineering & Hydrology Evidence
        </h3>

        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          Verified Government engineering inventory from the Central Water
          Commission, with NWDP/AP Surface Water observations where a current
          station can be safely matched.
        </p>
      </div>


      <div className="rounded-lg border p-4">
        <h4 className="mb-2 font-semibold">
          CWC Engineering Profile
        </h4>

        <Row
          label="CWC Project Identification Code"
          value={textValue(e.cwc_pic)}
        />

        <Row
          label="Official CWC Name"
          value={textValue(e.cwc_name)}
        />

        <Row
          label="River"
          value={textValue(e.river)}
        />

        <Row
          label="River Basin"
          value={textValue(e.river_basin)}
        />

        <Row
          label="Nearest City"
          value={textValue(e.nearest_city)}
        />

        <Row
          label="Structure Type"
          value={textValue(e.structure_type)}
        />

        <Row
          label="Official Structure Height"
          value={numericValue(e.height_m, "m")}
        />

        <Row
          label="Official CWC Structure Length"
          value={numericValue(e.length_m, "m")}
        />

        <Row
          label="Gross Storage Capacity"
          value={numericValue(e.gross_storage_mcm, "MCM", 6)}
        />

        <Row
          label="Effective Storage Capacity"
          value={numericValue(e.effective_storage_mcm, "MCM", 6)}
        />

        <Row
          label="Reservoir Area"
          value={numericValue(e.reservoir_area_m2, "m²", 0)}
        />

        <Row
          label="Designed Spillway Capacity"
          value={numericValue(
            e.spillway_capacity_cumecs,
            "m³/s",
            2,
          )}
        />

        <Row
          label="Purpose Code"
          value={textValue(e.purpose)}
        />

        <Row
          label="Completion Year"
          value={textValue(e.completion_year)}
        />

        <Row
          label="Seismic Zone"
          value={textValue(e.seismic_zone)}
        />

        <Row
          label="Official Latitude"
          value={numericValue(e.cwc_latitude, "°", 6)}
        />

        <Row
          label="Official Longitude"
          value={numericValue(e.cwc_longitude, "°", 6)}
        />
      </div>


      <div className="rounded-lg border p-4">
        <h4 className="mb-2 font-semibold">
          Current Hydrology Observations
        </h4>

        {h ? (
          <>
            <Row
              label="Water Level"
              value={numericValue(h.water_level_m, "m", 3)}
            />

            <Row
              label="Water-Level Station"
              value={textValue(h.level_station)}
            />

            <Row
              label="Water-Level Observation Time"
              value={dateValue(h.water_level_time)}
            />

            <Row
              label="Current Reservoir Storage"
              value={numericValue(
                h.current_storage_mcm,
                "MCM",
                3,
              )}
            />

            <Row
              label="Storage Station"
              value={textValue(h.storage_station)}
            />

            <Row
              label="Storage Observation Time"
              value={dateValue(h.storage_time)}
            />
          </>
        ) : (
          <div className="rounded-md bg-muted/40 p-3 text-sm leading-6 text-muted-foreground">
            No current NWDP station has been safely matched to this asset.
            SIMRAS does not fabricate a water-level or storage observation.
          </div>
        )}

        <p className="mt-3 text-xs leading-5 text-muted-foreground">
          Operational water level and reservoir storage are hydrology
          observations. They are not structural failure probabilities.
        </p>
      </div>


      <div className="rounded-lg border p-4">
        <h4 className="mb-2 font-semibold">
          Evidence & Provenance
        </h4>

        
            {/* SIMRAS_EVIDENCE_PROVENANCE_TABLE */}
            <div
              style={{
                width: "100%",
                overflowX: "auto",
                marginTop: 8,
              }}
            >
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  border:
                    "1px solid rgba(148,163,184,.18)",
                  background:
                    "rgba(8,20,32,.32)",
                }}
              >
                <thead>
                  <tr
                    style={{
                      background:
                        "rgba(15,35,52,.55)",
                      borderBottom:
                        "1px solid rgba(148,163,184,.22)",
                    }}
                  >
                    <th
                      style={{
                        padding: "10px 12px",
                        textAlign: "left",
                        color: "#7dd3fc",
                        fontSize: 11,
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: ".06em",
                      }}
                    >
                      Parameter
                    </th>

                    <th
                      style={{
                        padding: "10px 12px",
                        textAlign: "left",
                        color: "#7dd3fc",
                        fontSize: 11,
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: ".06em",
                      }}
                    >
                      Verified / Reported Value
                    </th>
                  </tr>
                </thead>

                <tbody>

              <tr
                style={{
                  borderBottom:
                    "1px solid rgba(148,163,184,.14)",
                }}
              >
                <td
                  style={{
                    width: "38%",
                    padding: "10px 12px",
                    color: "#94a3b8",
                    fontSize: 12,
                    fontWeight: 600,
                    verticalAlign: "top",
                  }}
                >
                  Source Authority
                </td>

                <td
                  style={{
                    padding: "10px 12px",
                    color: "#e2e8f0",
                    fontSize: 12,
                    fontWeight: 700,
                    verticalAlign: "top",
                    wordBreak: "break-word",
                  }}
                >
                  {textValue(e.source_authority)}
                </td>
              </tr>

              <tr
                style={{
                  borderBottom:
                    "1px solid rgba(148,163,184,.14)",
                }}
              >
                <td
                  style={{
                    width: "38%",
                    padding: "10px 12px",
                    color: "#94a3b8",
                    fontSize: 12,
                    fontWeight: 600,
                    verticalAlign: "top",
                  }}
                >
                  Source Document
                </td>

                <td
                  style={{
                    padding: "10px 12px",
                    color: "#e2e8f0",
                    fontSize: 12,
                    fontWeight: 700,
                    verticalAlign: "top",
                    wordBreak: "break-word",
                  }}
                >
                  {textValue(e.source_document)}
                </td>
              </tr>

              <tr
                style={{
                  borderBottom:
                    "1px solid rgba(148,163,184,.14)",
                }}
              >
                <td
                  style={{
                    width: "38%",
                    padding: "10px 12px",
                    color: "#94a3b8",
                    fontSize: 12,
                    fontWeight: 600,
                    verticalAlign: "top",
                  }}
                >
                  Evidence Class
                </td>

                <td
                  style={{
                    padding: "10px 12px",
                    color: "#e2e8f0",
                    fontSize: 12,
                    fontWeight: 700,
                    verticalAlign: "top",
                    wordBreak: "break-word",
                  }}
                >
                  {textValue(e.evidence_class)}
                </td>
              </tr>

              <tr
                style={{
                  borderBottom:
                    "1px solid rgba(148,163,184,.14)",
                }}
              >
                <td
                  style={{
                    width: "38%",
                    padding: "10px 12px",
                    color: "#94a3b8",
                    fontSize: 12,
                    fontWeight: 600,
                    verticalAlign: "top",
                  }}
                >
                  Quality Status
                </td>

                <td
                  style={{
                    padding: "10px 12px",
                    color: "#e2e8f0",
                    fontSize: 12,
                    fontWeight: 700,
                    verticalAlign: "top",
                    wordBreak: "break-word",
                  }}
                >
                  {textValue(e.quality_status)}
                </td>
              </tr>

              <tr
                style={{
                  borderBottom:
                    "1px solid rgba(148,163,184,.14)",
                }}
              >
                <td
                  style={{
                    width: "38%",
                    padding: "10px 12px",
                    color: "#94a3b8",
                    fontSize: 12,
                    fontWeight: 600,
                    verticalAlign: "top",
                  }}
                >
                  Asset Match Method
                </td>

                <td
                  style={{
                    padding: "10px 12px",
                    color: "#e2e8f0",
                    fontSize: 12,
                    fontWeight: 700,
                    verticalAlign: "top",
                    wordBreak: "break-word",
                  }}
                >
                  {textValue(e.match_method)}
                </td>
              </tr>

              <tr
                style={{
                  borderBottom:
                    "1px solid rgba(148,163,184,.14)",
                }}
              >
                <td
                  style={{
                    width: "38%",
                    padding: "10px 12px",
                    color: "#94a3b8",
                    fontSize: 12,
                    fontWeight: 600,
                    verticalAlign: "top",
                  }}
                >
                  Asset Match Score
                </td>

                <td
                  style={{
                    padding: "10px 12px",
                    color: "#e2e8f0",
                    fontSize: 12,
                    fontWeight: 700,
                    verticalAlign: "top",
                    wordBreak: "break-word",
                  }}
                >
                  {
            e.match_score === null ||
            e.match_score === undefined
              ? unavailable
              : `${(Number(e.match_score) * 100).toFixed(1)}%`
          }
                </td>
              </tr>

              <tr
                style={{
                  borderBottom:
                    "1px solid rgba(148,163,184,.14)",
                }}
              >
                <td
                  style={{
                    width: "38%",
                    padding: "10px 12px",
                    color: "#94a3b8",
                    fontSize: 12,
                    fontWeight: 600,
                    verticalAlign: "top",
                  }}
                >
                  Hydrology Authority
                </td>

                <td
                  style={{
                    padding: "10px 12px",
                    color: "#e2e8f0",
                    fontSize: 12,
                    fontWeight: 700,
                    verticalAlign: "top",
                    wordBreak: "break-word",
                  }}
                >
                  {textValue(h?.source_authority)}
                </td>
              </tr>
                </tbody>
              </table>
            </div>
      </div>


      <div className="rounded-lg border p-4">
        <h4 className="mb-2 font-semibold">
          Structural Prediction Status
        </h4>

        <Row
          label="Health Score"
          value="WITHHELD"
        />

        <Row
          label="Structural Risk"
          value="WITHHELD"
        />

        <Row
          label="Confidence"
          value="WITHHELD"
        />

        <Row
          label="Remaining Useful Life"
          value="WITHHELD"
        />

        <p className="mt-3 text-xs leading-5 text-muted-foreground">
          No rejected dam-condition transfer model is promoted into this
          report. AP structural inspection validation is still required.
        </p>
      </div>
    </section>
  );
}