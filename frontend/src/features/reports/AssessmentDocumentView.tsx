import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { apiRequest } from "../../services/api";

type RecordAny = Record<string, any>;

type Props = {
  assetCode: string;
};

type Column = {
  key: string;
  label: string;
  width?: string;
};

const panel: React.CSSProperties = {
  border: "1px solid rgba(148,163,184,.18)",
  borderRadius: 10,
  background: "rgba(7,18,29,.76)",
  overflow: "hidden",
};

function objectOf(
  value: unknown,
): RecordAny {
  return value &&
    typeof value === "object" &&
    !Array.isArray(value)
    ? value as RecordAny
    : {};
}

function arrayOf(
  value: unknown,
): any[] {
  return Array.isArray(value)
    ? value
    : [];
}

function valueText(
  value: unknown,
  fallback = "NOT AVAILABLE",
): string {
  if (
    value === undefined ||
    value === null ||
    value === ""
  ) {
    return fallback;
  }

  if (typeof value === "boolean") {
    return value ? "YES" : "NO";
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return fallback;
    }

    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(
          undefined,
          {
            maximumFractionDigits: 2,
          },
        );
  }

  if (typeof value === "object") {
    return fallback;
  }

  return String(value);
}

function scoreText(
  value: unknown,
): string {
  const number =
    Number(value);

  return Number.isFinite(number)
    ? `${number.toFixed(1)} / 100`
    : "WITHHELD";
}

function confidenceText(
  value: unknown,
): string {
  const number =
    Number(value);

  if (!Number.isFinite(number)) {
    return "WITHHELD";
  }

  const percentage =
    number <= 1
      ? number * 100
      : number;

  return `${Math.round(percentage)}%`;
}

function percentageText(
  value: unknown,
): string {
  const number =
    Number(value);

  if (!Number.isFinite(number)) {
    return "NOT AVAILABLE";
  }

  const percentage =
    number <= 1
      ? number * 100
      : number;

  return `${percentage.toFixed(1)}%`;
}

function dateText(
  value: unknown,
): string {
  if (!value) {
    return "NOT AVAILABLE";
  }

  const parsed =
    new Date(String(value));

  return Number.isNaN(
    parsed.getTime(),
  )
    ? String(value)
    : parsed.toLocaleString();
}

function SectionHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div
      style={{
        padding: "12px 15px",
        borderBottom:
          "1px solid rgba(148,163,184,.14)",
        background:
          "rgba(15,32,48,.68)",
      }}
    >
      <div
        style={{
          color: "#eef7fc",
          fontSize: 14,
          fontWeight: 800,
        }}
      >
        {title}
      </div>

      {subtitle ? (
        <div
          style={{
            marginTop: 3,
            color: "#8099ab",
            fontSize: 10,
          }}
        >
          {subtitle}
        </div>
      ) : null}
    </div>
  );
}

function Table({
  columns,
  rows,
  empty = "No validated records available.",
}: {
  columns: Column[];
  rows: RecordAny[];
  empty?: string;
}) {
  if (!rows.length) {
    return (
      <div
        style={{
          padding: 15,
          color: "#8297a7",
          fontSize: 11,
        }}
      >
        {empty}
      </div>
    );
  }

  return (
    <div
      style={{
        overflowX: "auto",
      }}
    >
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
        }}
      >
        <thead>
          <tr>
            {columns.map(
              (column) => (
                <th
                  key={column.key}
                  style={{
                    width: column.width,
                    padding: "9px 11px",
                    textAlign: "left",
                    background:
                      "rgba(3,14,24,.75)",
                    borderBottom:
                      "1px solid rgba(148,163,184,.18)",
                    color: "#8fb7d2",
                    fontSize: 9,
                    fontWeight: 800,
                    textTransform:
                      "uppercase",
                    letterSpacing:
                      ".05em",
                    verticalAlign:
                      "top",
                  }}
                >
                  {column.label}
                </th>
              ),
            )}
          </tr>
        </thead>

        <tbody>
          {rows.map(
            (
              row,
              rowIndex,
            ) => (
              <tr
                key={
                  row.id ??
                  rowIndex
                }
              >
                {columns.map(
                  (
                    column,
                    columnIndex,
                  ) => (
                    <td
                      key={
                        column.key
                      }
                      style={{
                        padding:
                          "10px 11px",
                        borderBottom:
                          "1px solid rgba(148,163,184,.1)",
                        color:
                          columnIndex === 0
                            ? "#dceaf3"
                            : "#c2d0da",
                        fontSize: 11,
                        fontWeight:
                          columnIndex === 0
                            ? 650
                            : 500,
                        lineHeight:
                          1.5,
                        verticalAlign:
                          "top",
                        overflowWrap:
                          "anywhere",
                      }}
                    >
                      {valueText(
                        row[
                          column.key
                        ],
                      )}
                    </td>
                  ),
                )}
              </tr>
            ),
          )}
        </tbody>
      </table>
    </div>
  );
}

function Kpi({
  title,
  value,
  detail,
}: {
  title: string;
  value: string;
  detail: string;
}) {
  const unavailable =
    value === "WITHHELD" ||
    value === "NOT AVAILABLE";

  return (
    <div
      style={{
        minHeight: 102,
        padding: 13,
        border:
          "1px solid rgba(148,163,184,.17)",
        borderRadius: 10,
        background:
          "linear-gradient(145deg,rgba(11,29,44,.95),rgba(6,17,28,.96))",
      }}
    >
      <div
        style={{
          color: "#819caf",
          fontSize: 9,
          fontWeight: 850,
          textTransform:
            "uppercase",
          letterSpacing:
            ".06em",
        }}
      >
        {title}
      </div>

      <div
        style={{
          marginTop: 8,
          color: unavailable
            ? "#f0c775"
            : "#f4f9fc",
          fontSize: 20,
          fontWeight: 850,
        }}
      >
        {value}
      </div>

      <div
        style={{
          marginTop: 6,
          color: "#7e94a5",
          fontSize: 9,
          lineHeight: 1.4,
        }}
      >
        {detail}
      </div>
    </div>
  );
}

function normalizeEvidence(
  root: RecordAny,
): RecordAny[] {
  const candidates = [
    root.government_evidence,
    root.government_standards,
    root.evidence_and_standards,
    root.evidence,
  ];

  let values: any[] = [];

  for (
    const candidate
    of candidates
  ) {
    if (Array.isArray(candidate)) {
      values = candidate;
      break;
    }

    const record =
      objectOf(candidate);

    if (
      Array.isArray(
        record.records,
      )
    ) {
      values =
        record.records;
      break;
    }

    if (
      Array.isArray(
        record.rows,
      )
    ) {
      values =
        record.rows;
      break;
    }
  }

  return values.map(
    (
      raw,
      index,
    ) => {
      const row =
        objectOf(raw);

      return {
        id: index,

        evidence:
          row.evidence ??
          row.requirement ??
          row.item ??
          row.name ??
          row.parameter ??
          row.field_name,

        measured:
          row.measured_value ??
          row.current_value ??
          row.value,

        threshold:
          row.threshold ??
          row.reference ??
          row.expected ??
          row.expected_range,

        compliance:
          row.compliance ??
          row.status ??
          row.quality_flag,

        source:
          row.source ??
          row.authority ??
          row.document ??
          row.source_name,
      };
    },
  );
}

function normalizeRecommendations(
  root: RecordAny,
): RecordAny[] {
  let values =
    arrayOf(
      root.recommendations,
    );

  if (!values.length) {
    values =
      arrayOf(
        root.risk?.recommendations,
      );
  }

  return values.map(
    (
      raw,
      index,
    ) => {
      if (
        typeof raw ===
        "string"
      ) {
        return {
          id: index,
          priority:
            root.risk?.level ??
            "FOLLOW-UP",
          recommendation:
            raw,
          reason:
            "See assessment evidence.",
          evidence:
            "Selected asset assessment",
          benefit:
            "NOT QUANTIFIED",
          timeframe:
            "NOT SPECIFIED",
        };
      }

      const row =
        objectOf(raw);

      return {
        id: index,
        priority:
          row.priority ??
          row.level ??
          row.severity,

        recommendation:
          row.recommendation ??
          row.action ??
          row.title,

        reason:
          row.reason ??
          row.rationale,

        evidence:
          Array.isArray(
            row.supporting_evidence,
          )
            ? row.supporting_evidence.join(
                " | ",
              )
            : (
                row.supporting_evidence ??
                row.evidence
              ),

        benefit:
          row.expected_benefit ??
          row.benefit,

        timeframe:
          row.suggested_timeframe ??
          row.timeframe,
      };
    },
  );
}



/* SIMRAS_REAL_HISTORY_GRAPHS_V1 */

function HistoricalTrendChart({
  title,
  history,
}: {
  title: string;
  history: any[];
}) {

  const observations =
    history
      .map(
        (
          raw,
          index,
        ) => {

          const row =
            objectOf(raw);


          const numeric =
            Number(
              row.value ??
              row.current_value ??
              row.measurement ??
              row.observed_value ??
              row.y
            );


          const time =
            row.timestamp ??
            row.observed_at ??
            row.datetime ??
            row.date ??
            row.time ??
            row.x;


          return {
            index,
            value: numeric,
            time,
          };
        },
      )
      .filter(
        (
          row,
        ) =>
          Number.isFinite(
            row.value,
          ),
      );


  if (
    observations.length <
    2
  ) {
    return null;
  }


  const width =
    820;

  const height =
    230;

  const left =
    58;

  const right =
    20;

  const top =
    20;

  const bottom =
    38;


  const values =
    observations.map(
      (
        row,
      ) =>
        row.value,
    );


  const minimum =
    Math.min(
      ...values,
    );


  const maximum =
    Math.max(
      ...values,
    );


  const span =
    maximum -
    minimum ||
    1;


  const padding =
    span *
    0.08;


  const chartMin =
    minimum -
    padding;


  const chartMax =
    maximum +
    padding;


  const chartSpan =
    chartMax -
    chartMin ||
    1;


  const points =
    observations
      .map(
        (
          row,
          index,
        ) => {

          const x =
            left +
            (
              index /
              Math.max(
                observations.length -
                1,
                1,
              )
            ) *
              (
                width -
                left -
                right
              );


          const y =
            top +
            (
              1 -
              (
                row.value -
                chartMin
              ) /
                chartSpan
            ) *
              (
                height -
                top -
                bottom
              );


          return (
            String(x) +
            "," +
            String(y)
          );
        },
      )
      .join(" ");


  const gridLevels =
    [
      0,
      0.25,
      0.5,
      0.75,
      1,
    ];


  const firstTime =
    observations[
      0
    ]?.time;


  const middleTime =
    observations[
      Math.floor(
        observations.length /
        2
      )
    ]?.time;


  const lastTime =
    observations[
      observations.length -
        1
    ]?.time;


  return (
    <article
      style={{
        border:
          "1px solid rgba(148,163,184,.17)",
        borderRadius: 10,
        overflow: "hidden",
        background:
          "rgba(5,15,25,.72)",
      }}
    >

      <div
        style={{
          padding:
            "11px 14px",
          borderBottom:
            "1px solid rgba(148,163,184,.12)",
          background:
            "rgba(15,32,48,.55)",
        }}
      >

        <div
          style={{
            color:
              "#dcecf6",
            fontSize: 12,
            fontWeight: 800,
          }}
        >
          {title}
        </div>

        <div
          style={{
            marginTop: 3,
            color:
              "#758ea1",
            fontSize: 9,
          }}
        >
          {
            observations.length
          } stored observations
        </div>

      </div>


      <div
        style={{
          padding:
            "8px 10px 4px",
          overflowX:
            "hidden",
        }}
      >

        <svg
          viewBox={
            "0 0 " +
            width +
            " " +
            height
          }
          role="img"
          aria-label={
            title +
            " historical trend"
          }
          style={{
            display:
              "block",
            width:
              "100%",
            height:
              "220px",
          }}
        >

          {
            gridLevels.map(
              (
                ratio,
              ) => {

                const y =
                  top +
                  ratio *
                    (
                      height -
                      top -
                      bottom
                    );


                const labelValue =
                  chartMax -
                  ratio *
                    chartSpan;


                return (
                  <g
                    key={
                      ratio
                    }
                  >

                    <line
                      x1={
                        left
                      }
                      x2={
                        width -
                        right
                      }
                      y1={
                        y
                      }
                      y2={
                        y
                      }
                      stroke="rgba(148,163,184,.13)"
                      strokeWidth="1"
                    />


                    <text
                      x={
                        left -
                        7
                      }
                      y={
                        y + 3
                      }
                      textAnchor="end"
                      fill="#71879a"
                      fontSize="9"
                    >
                      {
                        labelValue.toFixed(
                          2,
                        )
                      }
                    </text>

                  </g>
                );
              },
            )
          }


          <line
            x1={
              left
            }
            y1={
              height -
              bottom
            }
            x2={
              width -
              right
            }
            y2={
              height -
              bottom
            }
            stroke="rgba(148,163,184,.25)"
            strokeWidth="1"
          />


          <line
            x1={
              left
            }
            y1={
              top
            }
            x2={
              left
            }
            y2={
              height -
              bottom
            }
            stroke="rgba(148,163,184,.25)"
            strokeWidth="1"
          />


          <polyline
            points={
              points
            }
            fill="none"
            stroke="#38bdf8"
            strokeWidth="2.6"
            strokeLinejoin="round"
            strokeLinecap="round"
          />


          {
            observations.length <=
            35
              ? observations.map(
                  (
                    row,
                    index,
                  ) => {

                    const x =
                      left +
                      (
                        index /
                        Math.max(
                          observations.length -
                            1,
                          1,
                        )
                      ) *
                        (
                          width -
                          left -
                          right
                        );


                    const y =
                      top +
                      (
                        1 -
                        (
                          row.value -
                          chartMin
                        ) /
                          chartSpan
                      ) *
                        (
                          height -
                          top -
                          bottom
                        );


                    return (
                      <circle
                        key={
                          index
                        }
                        cx={
                          x
                        }
                        cy={
                          y
                        }
                        r="2.4"
                        fill="#bae6fd"
                      />
                    );
                  },
                )
              : null
          }


          <text
            x={
              left
            }
            y={
              height -
              10
            }
            fill="#70879a"
            fontSize="9"
          >
            {
              dateText(
                firstTime,
              )
            }
          </text>


          <text
            x={
              width /
              2
            }
            y={
              height -
              10
            }
            textAnchor="middle"
            fill="#70879a"
            fontSize="9"
          >
            {
              dateText(
                middleTime,
              )
            }
          </text>


          <text
            x={
              width -
              right
            }
            y={
              height -
              10
            }
            textAnchor="end"
            fill="#70879a"
            fontSize="9"
          >
            {
              dateText(
                lastTime,
              )
            }
          </text>

        </svg>

      </div>

    </article>
  );
}

export function AssessmentDocumentView({
  assetCode,
}: Props) {
  const [
    data,
    setData,
  ] =
    useState<RecordAny | null>(
      null,
    );

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    error,
    setError,
  ] =
    useState<string | null>(
      null,
    );


  useEffect(
    () => {
      let active =
        true;

      setLoading(true);
      setError(null);

      apiRequest<RecordAny>(
        `/api/v1/reports/assets/${encodeURIComponent(
          assetCode,
        )}/assessment`,
      )
        .then(
          (
            response,
          ) => {
            if (active) {
              setData(
                response,
              );
            }
          },
        )
        .catch(
          (
            cause,
          ) => {
            if (active) {
              setError(
                cause instanceof
                  Error
                  ? cause.message
                  : "Assessment request failed.",
              );
            }
          },
        )
        .finally(
          () => {
            if (active) {
              setLoading(
                false,
              );
            }
          },
        );

      return () => {
        active =
          false;
      };
    },
    [assetCode],
  );


  const model =
    useMemo(
      () => {
        const root =
          data ?? {};

        const asset =
          objectOf(
            root.asset,
          );

        const health =
          objectOf(
            root.health,
          );

        const risk =
          objectOf(
            root.risk,
          );

        const rul =
          objectOf(
            root.rul ??
            root.remaining_useful_life,
          );

        const transparency =
          objectOf(
            root.transparency,
          );


        const supporting =
          arrayOf(
            root.supporting_data,
          ).map(
            (
              raw,
              index,
            ) => {
              const row =
                objectOf(raw);

              let expected =
                row.expected_range ??
                row.historical_range ??
                row.reference;

              if (
                Array.isArray(
                  expected,
                )
              ) {
                expected =
                  expected.join(
                    " - ",
                  );
              }

              return {
                id: index,

                input:
                  row.input ??
                  row.name ??
                  row.parameter,

                current:
                  row.current_value ===
                    null ||
                  row.current_value ===
                    undefined
                    ? "NOT AVAILABLE"
                    : `${valueText(
                        row.current_value,
                      )}${
                        row.unit
                          ? ` ${row.unit}`
                          : ""
                      }`,

                expected,

                status:
                  row.status ??
                  row.quality_flag ??
                  row.reference_type,

                trend:
                  row.trend ??
                  "INSUFFICIENT_HISTORY",

                updated:
                  dateText(
                    row.last_updated ??
                    row.timestamp,
                  ),

                usedByModel:
                  row.used_by_model,

                history:
                  arrayOf(
                    row.history ??
                    row.series ??
                    row.points ??
                    row.observations
                  ),
              };
            },
          );


        const factors =
          supporting.map(
            (
              row,
              index,
            ) => ({
              id: index,
              factor:
                row.input,
              current:
                row.current,
              reference:
                row.expected,
              impact:
                row.usedByModel ===
                  true
                  ? "Used by active model"
                  : "Available context; not used by active model",
            }),
          );


        const notes =
          Array.from(
            new Set(
              [
                ...arrayOf(
                  health.factors,
                ),
                ...arrayOf(
                  risk.factors,
                ),
                risk.failure_probability_note,
                rul.reason,
              ].filter(
                (
                  value,
                ): value is string =>
                  typeof value ===
                    "string" &&
                  value.trim()
                    .length >
                    0,
              ),
            ),
          );


        const evidence =
          normalizeEvidence(
            root,
          );


        const recommendations =
          normalizeRecommendations(
            root,
          );


        const modelParts =
          [
            transparency.model_name,
            transparency.model_version,
          ].filter(
            Boolean,
          );


        const modelName =
          transparency.model ??
          (
            modelParts.length
              ? modelParts.join(
                  " · ",
                )
              : "NOT AVAILABLE"
          );


        const transparencyRows =
          [
            {
              field:
                "Prediction",
              value:
                transparency.prediction ??
                risk.level ??
                "WITHHELD",
            },

            {
              field:
                "Confidence",
              value:
                confidenceText(
                  transparency.confidence ??
                  risk.confidence,
                ),
            },

            {
              field:
                "Model",
              value:
                modelName,
            },

            {
              field:
                "Prediction method",
              value:
                transparency.prediction_method ??
                "NOT AVAILABLE",
            },

            {
              field:
                "Feature version",
              value:
                transparency.feature_version ??
                "NOT AVAILABLE",
            },

            {
              field:
                "Prediction generated",
              value:
                dateText(
                  transparency.prediction_generated_at ??
                  root.generated_at,
                ),
            },

            {
              field:
                "Data points used",
              value:
                transparency.data_points_used ??
                transparency.model_input_count ??
                "NOT AVAILABLE",
            },

            {
              field:
                "Evidence records available",
              value:
                transparency.evidence_record_count ??
                evidence.length,
            },

            {
              field:
                "Model stage",
              value:
                transparency.model_stage ??
                "NOT AVAILABLE",
            },
          ];


        return {
          root,
          asset,
          health,
          risk,
          rul,
          supporting,
          factors,
          notes,
          evidence,
          recommendations,
          transparencyRows,
        };
      },
      [data],
    );


  if (loading) {
    return (
      <div
        style={{
          ...panel,
          padding: 22,
          color: "#94a3b8",
        }}
      >
        Loading selected asset assessment...
      </div>
    );
  }


  if (
    error ||
    !data
  ) {
    return (
      <div
        style={{
          ...panel,
          padding: 22,
          color: "#fca5a5",
        }}
      >
        Assessment unavailable:
        {" "}
        {error ??
          "No assessment response."}
      </div>
    );
  }


  const {
    root,
    asset,
    health,
    risk,
    rul,
    supporting,
    factors,
    notes,
    evidence,
    recommendations,
    transparencyRows,
  } =
    model;


  const healthValue =
    health.available ===
      false ||
    health.score ===
      undefined ||
    health.score ===
      null
      ? "WITHHELD"
      : scoreText(
          health.score,
        );


  const riskScore =
    risk.score ===
      undefined ||
    risk.score ===
      null
      ? "WITHHELD"
      : scoreText(
          risk.score,
        );


  const riskLevel =
    valueText(
      risk.level,
      "WITHHELD",
    );


  const confidenceValue =
    confidenceText(
      risk.confidence,
    );


  const rulNumber =
    rul.years ??
    rul.estimate_years ??
    rul.rul_years ??
    rul.value;


  const rulValue =
    rulNumber ===
      undefined ||
    rulNumber ===
      null
      ? "WITHHELD"
      : `${valueText(
          rulNumber,
        )} years`;


  const riskRows =
    [
      {
        field:
          "Risk score",
        value:
          riskScore,
      },

      {
        field:
          "Risk level",
        value:
          riskLevel,
      },

      {
        field:
          "Risk confidence",
        value:
          confidenceValue,
      },

      {
        field:
          "Poor-condition probability",
        value:
          percentageText(
            risk.poor_condition_probability,
          ),
      },

      {
        field:
          "Structural failure probability",
        value:
          percentageText(
            risk.failure_probability,
          ),
      },
    ];


  const rulRows =
    [
      {
        field:
          "Remaining Useful Life",
        value:
          rulValue,
      },

      {
        field:
          "Lower estimate",
        value:
          rul.lower_bound ??
          rul.lower_bound_years ??
          "WITHHELD",
      },

      {
        field:
          "Upper estimate",
        value:
          rul.upper_bound ??
          rul.upper_bound_years ??
          "WITHHELD",
      },

      {
        field:
          "Status / reason",
        value:
          rul.reason ??
          (
            rulValue ===
              "WITHHELD"
              ? "Longitudinal deterioration evidence is required."
              : "AVAILABLE"
          ),
      },
    ];


  return (
    <div
      data-simras-assessment-document="v3"
      style={{
        width: "100%",
        maxWidth: 1500,
        margin: "0 auto",
        display: "grid",
        gap: 13,
      }}
    >

      <section
        style={{
          ...panel,
          padding:
            "18px 20px",
          border:
            "1px solid rgba(56,189,248,.24)",
        }}
      >
        <div
          style={{
            color: "#55c7f3",
            fontSize: 9,
            fontWeight: 900,
            letterSpacing:
              ".08em",
            textTransform:
              "uppercase",
          }}
        >
          SIMRAS AI-Powered Asset Health Assessment
        </div>

        <h2
          style={{
            margin:
              "7px 0 0",
            color: "#f4f9fc",
            fontSize: 23,
            fontWeight: 850,
          }}
        >
          {valueText(
            asset.name,
            assetCode,
          )}
        </h2>

        <div
          style={{
            marginTop: 14,
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit,minmax(200px,1fr))",
            gap: 9,
          }}
        >
          {[
            [
              "Report ID",
              root.report_id,
            ],
            [
              "Asset",
              asset.asset_code ??
              assetCode,
            ],
            [
              "Infrastructure",
              asset.asset_type,
            ],
            [
              "District",
              asset.district,
            ],
            [
              "Generated",
              dateText(
                root.generated_at,
              ),
            ],
            [
              "Status",
              asset.status,
            ],
          ].map(
            (
              [
                label,
                value,
              ],
            ) => (
              <div
                key={String(
                  label,
                )}
              >
                <div
                  style={{
                    color: "#718b9f",
                    fontSize: 8,
                    fontWeight: 800,
                    textTransform:
                      "uppercase",
                  }}
                >
                  {label}
                </div>

                <div
                  style={{
                    marginTop: 3,
                    color: "#dbe8f1",
                    fontSize: 11,
                    fontWeight: 650,
                  }}
                >
                  {valueText(
                    value,
                  )}
                </div>
              </div>
            ),
          )}
        </div>
      </section>


      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(auto-fit,minmax(170px,1fr))",
          gap: 9,
        }}
      >
        <Kpi
          title="Health Score"
          value={healthValue}
          detail="Current structural / condition assessment"
        />

        <Kpi
          title="Risk Level"
          value={riskLevel}
          detail="Selected-asset risk classification"
        />

        <Kpi
          title="Risk Score"
          value={riskScore}
          detail="Decision-support estimate"
        />

        <Kpi
          title="Confidence"
          value={confidenceValue}
          detail="Current prediction confidence"
        />

        <Kpi
          title="Remaining Useful Life"
          value={rulValue}
          detail="Longitudinal evidence gated"
        />
      </div>


      <section style={panel}>
        <SectionHeader
          title="Health Score"
        />

        <div
          style={{
            padding:
              "13px 15px",
          }}
        >
          <div
            style={{
              color: "#eef7fc",
              fontSize: 20,
              fontWeight: 850,
            }}
          >
            {healthValue}
          </div>

          {notes.length ? (
            <ul
              style={{
                margin:
                  "10px 0 0 17px",
                padding: 0,
                color: "#bdccd6",
                fontSize: 11,
                lineHeight: 1.65,
              }}
            >
              {notes.map(
                (
                  note,
                  index,
                ) => (
                  <li
                    key={index}
                  >
                    {note}
                  </li>
                ),
              )}
            </ul>
          ) : null}
        </div>
      </section>


      <section style={panel}>
        <SectionHeader
          title="Risk Assessment"
        />

        <Table
          columns={[
            {
              key: "field",
              label: "Assessment",
              width: "38%",
            },
            {
              key: "value",
              label: "Current Result",
            },
          ]}
          rows={riskRows}
        />
      </section>


      <section style={panel}>
        <SectionHeader
          title="Remaining Useful Life (RUL)"
        />

        <Table
          columns={[
            {
              key: "field",
              label: "RUL Field",
              width: "38%",
            },
            {
              key: "value",
              label: "Value",
            },
          ]}
          rows={rulRows}
        />
      </section>


      <section style={panel}>
        <SectionHeader
          title="Why did the AI make this prediction?"
          subtitle="Stored model inputs are displayed without inventing SHAP values."
        />

        <Table
          columns={[
            {
              key: "factor",
              label: "Factor",
              width: "23%",
            },
            {
              key: "current",
              label: "Current Value",
              width: "20%",
            },
            {
              key: "reference",
              label: "Expected / Reference",
              width: "22%",
            },
            {
              key: "impact",
              label: "Impact",
            },
          ]}
          rows={factors}
        />
      </section>


      <section style={panel}>
        <SectionHeader
          title="Government Evidence & Standards"
          subtitle="No missing regulatory threshold is inferred."
        />

        <Table
          columns={[
            {
              key: "evidence",
              label:
                "Evidence / Requirement",
              width: "24%",
            },
            {
              key: "measured",
              label:
                "Measured Value",
              width: "16%",
            },
            {
              key: "threshold",
              label: "Threshold",
              width: "17%",
            },
            {
              key: "compliance",
              label: "Compliance",
              width: "18%",
            },
            {
              key: "source",
              label: "Source",
            },
          ]}
          rows={evidence}
          empty="No qualifying government evidence rows are linked to this asset."
        />
      </section>


      <section style={panel}>
        <SectionHeader
          title="Recommendations"
        />

        <Table
          columns={[
            {
              key: "priority",
              label: "Priority",
              width: "9%",
            },
            {
              key: "recommendation",
              label: "Recommendation",
              width: "25%",
            },
            {
              key: "reason",
              label: "Reason",
              width: "20%",
            },
            {
              key: "evidence",
              label:
                "Supporting Evidence",
              width: "23%",
            },
            {
              key: "benefit",
              label:
                "Expected Benefit",
              width: "12%",
            },
            {
              key: "timeframe",
              label: "Timeframe",
              width: "11%",
            },
          ]}
          rows={recommendations}
        />
      </section>


      <section style={panel}>
        <SectionHeader
          title="Supporting Data"
        />

        <Table
          columns={[
            {
              key: "input",
              label: "Input",
              width: "18%",
            },
            {
              key: "current",
              label: "Current Value",
              width: "18%",
            },
            {
              key: "expected",
              label:
                "Expected / Historical Range",
              width: "22%",
            },
            {
              key: "status",
              label: "Status",
              width: "16%",
            },
            {
              key: "trend",
              label: "Trend",
              width: "13%",
            },
            {
              key: "updated",
              label: "Last Updated",
              width: "13%",
            },
          ]}
          rows={supporting}
        />
      </section>


      <section
        style={{
          ...panel,
          paddingBottom: 14,
        }}
      >

        <SectionHeader
          title="Historical Trends"
          subtitle="Dynamic line graphs generated only from stored selected-asset historical observations."
        />


        {
          supporting.some(
            (
              row,
            ) =>
              Array.isArray(
                row.history,
              ) &&
              row.history.filter(
                (
                  point: any,
                ) => {

                  const record =
                    objectOf(
                      point,
                    );


                  return Number.isFinite(
                    Number(
                      record.value ??
                      record.current_value ??
                      record.measurement ??
                      record.observed_value ??
                      record.y
                    ),
                  );
                },
              ).length >=
                2,
          )
            ? (
              <div
                style={{
                  padding:
                    "14px",
                  display:
                    "grid",
                  gridTemplateColumns:
                    "repeat(auto-fit,minmax(420px,1fr))",
                  gap:
                    "12px",
                }}
              >

                {
                  supporting
                    .filter(
                      (
                        row,
                      ) =>
                        Array.isArray(
                          row.history,
                        ) &&
                        row.history.filter(
                          (
                            point: any,
                          ) => {

                            const record =
                              objectOf(
                                point,
                              );


                            return Number.isFinite(
                              Number(
                                record.value ??
                                record.current_value ??
                                record.measurement ??
                                record.observed_value ??
                                record.y
                              ),
                            );
                          },
                        ).length >=
                          2,
                    )
                    .map(
                      (
                        row,
                        index,
                      ) => (
                        <HistoricalTrendChart
                          key={
                            String(
                              row.input ??
                              index,
                            )
                          }
                          title={
                            valueText(
                              row.input,
                              "Metric",
                            ) +
                            " trend"
                          }
                          history={
                            row.history
                          }
                        />
                      ),
                    )
                }

              </div>
            )
            : (
              <div
                style={{
                  margin:
                    "14px",
                  padding:
                    "14px",
                  border:
                    "1px dashed rgba(148,163,184,.22)",
                  borderRadius:
                    8,
                  color:
                    "#8196a7",
                  fontSize:
                    11,
                  lineHeight:
                    1.55,
                }}
              >
                INSUFFICIENT HISTORICAL DATA
                <br />
                No stored metric currently contains at least two validated observations, so SIMRAS will not fabricate a trend graph.
              </div>
            )
        }

      </section>


      <section style={panel}>
        <SectionHeader
          title="Prediction Transparency"
        />

        <Table
          columns={[
            {
              key: "field",
              label:
                "Prediction Field",
              width: "38%",
            },
            {
              key: "value",
              label: "Value",
            },
          ]}
          rows={
            transparencyRows
          }
        />
      </section>

    </div>
  );
}

export default AssessmentDocumentView;
