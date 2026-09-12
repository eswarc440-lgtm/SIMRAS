import { useEffect, useState } from "react";

import { bridgeReportProfile } from "../../services/simrasTwinApi";


type BridgeProfileResponse = {
  available?: boolean;

  asset?: {
    asset_code?: string | null;
    name?: string | null;
    district?: string | null;
    built_year?: number | null;
    identity_status?: string | null;
  } | null;

  engineering?: {
    bridge_type?: string | null;

    actual_length_m?: number | null;

    reported_width_m?: number | null;
    width_basis?: string | null;

    lanes_reported?: number | null;

    material_reported?: string | null;

    verified_pier_count?: number | null;
    pier_count_status?: string | null;

    latitude?: number | null;
    longitude?: number | null;

    geometry_source?: string | null;

    rendering_strategy?: string | null;
    rendering_estimated?: boolean | null;

    profile_version?: string | null;

    osm_way_id?: number | null;

    structure_key?: string | null;

    updated_at?: string | null;
  } | null;

  readiness?: {
    health_score?: number | null;
    health_status?: string | null;

    risk_score?: number | null;
    risk_level?: string | null;
    risk_status?: string | null;

    confidence?: number | null;
    confidence_status?: string | null;

    rul_years?: number | null;
    rul_status?: string | null;

    geometry_status?: string | null;
    engineering_status?: string | null;
    evidence_status?: string | null;

    report_version?: string | null;
    updated_at?: string | null;
  } | null;
};


type Props = {
  assetCode?: string | null;
};


function formatText(
  value: unknown,
): string {
  if (
    value === undefined ||
    value === null ||
    value === ""
  ) {
    return "NOT AVAILABLE";
  }

  return String(value)
    .replaceAll("_", " ");
}


function formatNumber(
  value: number | null | undefined,
  unit = "",
  digits = 2,
): string {
  if (
    value === undefined ||
    value === null ||
    Number.isNaN(Number(value))
  ) {
    return "NOT AVAILABLE";
  }

  const rendered = Number(value).toLocaleString(
    undefined,
    {
      maximumFractionDigits: digits,
    },
  );

  return unit
    ? `${rendered} ${unit}`
    : rendered;
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
      style={{
        display: "grid",
        gridTemplateColumns:
          "minmax(180px, .9fr) minmax(240px, 1.3fr)",
        gap: 16,
        padding: "10px 0",
        borderBottom:
          "1px solid rgba(148,163,184,.12)",
      }}
    >
      <div
        style={{
          color: "#93c5fd",
          fontSize: 12,
        }}
      >
        {label}
      </div>

      <div
        style={{
          color: "#f8fafc",
          fontSize: 12,
          fontWeight: 700,
          overflowWrap: "anywhere",
        }}
      >
        {value}
      </div>
    </div>
  );
}


export default function BridgeEngineeringEvidence({
  assetCode,
}: Props) {
  const [profile, setProfile] =
    useState<BridgeProfileResponse | null>(null);

  const [loading, setLoading] =
    useState(false);


  useEffect(() => {
    let active = true;

    if (!assetCode) {
      setProfile(null);

      return () => {
        active = false;
      };
    }


    setLoading(true);


    bridgeReportProfile(assetCode)
      .then((result: BridgeProfileResponse) => {
        if (active) {
          setProfile(result);
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
      <section
        style={{
          border:
            "1px solid rgba(56,189,248,.18)",
          borderRadius: 12,
          padding: 18,
          background:
            "rgba(7,22,35,.45)",
        }}
      >
        Loading verified bridge engineering evidence...
      </section>
    );
  }


  if (
    !profile?.available ||
    !profile.engineering
  ) {
    return null;
  }


  const e = profile.engineering;
  const r = profile.readiness;
  const a = profile.asset;


  return (
    <section
      data-simras-bridge-engineering="ready"
      style={{
        border:
          "1px solid rgba(56,189,248,.24)",
        borderRadius: 12,
        padding: 18,
        background:
          "rgba(7,22,35,.58)",
      }}
    >
      <div
        style={{
          color: "#7dd3fc",
          fontSize: 15,
          fontWeight: 800,
          marginBottom: 4,
        }}
      >
        Verified Bridge Engineering Evidence
      </div>

      <div
        style={{
          color: "#94a3b8",
          fontSize: 12,
          lineHeight: 1.6,
          marginBottom: 14,
        }}
      >
        Factual bridge inventory and engineering evidence used by
        the digital twin. Rendering-only dimensions are never
        presented as engineering facts.
      </div>


      <Row
        label="Bridge type"
        value={formatText(e.bridge_type)}
      />

      <Row
        label="Engineering length"
        value={formatNumber(
          e.actual_length_m,
          "m",
          2,
        )}
      />

      <Row
        label="Deck width"
        value={
          e.reported_width_m !== null &&
          e.reported_width_m !== undefined
            ? formatNumber(
                e.reported_width_m,
                "m",
              )
            : "NOT AVAILABLE — no factual width stored"
        }
      />

      <Row
        label="Width evidence"
        value={formatText(e.width_basis)}
      />

      <Row
        label="Verified piers"
        value={formatNumber(
          e.verified_pier_count,
        )}
      />

      <Row
        label="Pier evidence"
        value={formatText(
          e.pier_count_status,
        )}
      />

      <Row
        label="Material"
        value={formatText(
          e.material_reported,
        )}
      />

      <Row
        label="Reported lanes / tracks"
        value={formatNumber(
          e.lanes_reported,
        )}
      />

      <Row
        label="Completion year"
        value={formatNumber(
          a?.built_year,
          "",
          0,
        )}
      />

      <Row
        label="Latitude"
        value={formatNumber(
          e.latitude,
          "°",
          6,
        )}
      />

      <Row
        label="Longitude"
        value={formatNumber(
          e.longitude,
          "°",
          6,
        )}
      />

      <Row
        label="Geometry source"
        value={formatText(
          e.geometry_source,
        )}
      />

      <Row
        label="Geometry status"
        value={formatText(
          r?.geometry_status,
        )}
      />

      <Row
        label="Engineering status"
        value={formatText(
          r?.engineering_status,
        )}
      />

      <Row
        label="Evidence status"
        value={formatText(
          r?.evidence_status,
        )}
      />

      <Row
        label="Rendering strategy"
        value={formatText(
          e.rendering_strategy,
        )}
      />

      <Row
        label="Profile version"
        value={formatText(
          e.profile_version,
        )}
      />


      <div
        style={{
          marginTop: 16,
          border:
            "1px solid rgba(251,191,36,.18)",
          borderRadius: 8,
          padding: 12,
          background:
            "rgba(120,53,15,.08)",
          color: "#cbd5e1",
          fontSize: 12,
          lineHeight: 1.65,
        }}
      >
        <strong>
          Structural prediction policy:
        </strong>{" "}

        Health remains{" "}
        <strong>
          {r?.health_score == null
            ? "WITHHELD"
            : formatNumber(r.health_score)}
        </strong>
        . Confidence remains{" "}
        <strong>
          {r?.confidence == null
            ? "WITHHELD"
            : formatNumber(r.confidence)}
        </strong>
        . Remaining Useful Life remains{" "}
        <strong>
          {r?.rul_years == null
            ? "WITHHELD"
            : formatNumber(
                r.rul_years,
                "years",
              )}
        </strong>
        . An inventory condition label is not treated as a
        structural inspection-derived Health Score.
      </div>
    </section>
  );
}