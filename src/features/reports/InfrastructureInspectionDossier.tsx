import { useEffect, useMemo, useState, type ReactNode } from "react";

type Props = {
  asset: any;
};

type AnyRow = Record<string, any>;

const show = (value: any, fallback = "NOT AVAILABLE") =>
  value === null || value === undefined || value === ""
    ? fallback
    : String(value);

const label = (key: string) =>
  key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

function Section({
  number,
  title,
  children,
}: {
  number: number;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3 bg-slate-50 border-b border-slate-200">
        <span className="flex h-7 w-7 items-center justify-center rounded bg-[#0B3B63] text-white text-xs font-bold">
          {number}
        </span>

        <h2 className="font-bold text-sm text-slate-900 uppercase tracking-wide">
          {title}
        </h2>
      </div>

      <div className="p-4">{children}</div>
    </section>
  );
}

function Field({
  title,
  value,
}: {
  title: string;
  value: ReactNode;
}) {
  return (
    <div className="border border-slate-200 rounded-md p-3 bg-white">
      <div className="text-[10px] uppercase font-bold tracking-wide text-slate-500">
        {title}
      </div>

      <div className="mt-1 text-sm font-semibold text-slate-900 break-words">
        {value}
      </div>
    </div>
  );
}

export default function InfrastructureInspectionDossier({ asset }: Props) {
  const [liveAsset, setLiveAsset] = useState<any>(asset);
  const [inspections, setInspections] = useState<AnyRow[]>([]);
  const [maintenance, setMaintenance] = useState<AnyRow[]>([]);
  const [loading, setLoading] = useState(true);

  const assetCode = asset?.asset_code ?? asset?.id ?? "";

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);

      try {
        const [assetResponse, inspectionResponse, maintenanceResponse] =
          await Promise.all([
            fetch("/api/v1/assets?limit=1000"),
            fetch("/api/v1/inspections?limit=1000"),
            fetch("/api/v1/maintenance?limit=1000"),
          ]);

        const assetData = assetResponse.ok
          ? await assetResponse.json()
          : {};

        const inspectionData = inspectionResponse.ok
          ? await inspectionResponse.json()
          : [];

        const maintenanceData = maintenanceResponse.ok
          ? await maintenanceResponse.json()
          : [];

        if (!active) return;

        const assetRows = Array.isArray(assetData)
          ? assetData
          : Array.isArray(assetData?.items)
            ? assetData.items
            : [];

        const inspectionRows = Array.isArray(inspectionData)
          ? inspectionData
          : inspectionData?.items ?? [];

        const maintenanceRows = Array.isArray(maintenanceData)
          ? maintenanceData
          : maintenanceData?.items ?? [];

        const matchedAsset =
          assetRows.find(
            (row: AnyRow) =>
              String(row.asset_code ?? row.id) === String(assetCode),
          ) ?? asset;

        setLiveAsset(matchedAsset);

        setInspections(
          inspectionRows
            .filter(
              (row: AnyRow) =>
                String(row.asset_code) === String(assetCode),
            )
            .sort(
              (a: AnyRow, b: AnyRow) =>
                new Date(b.inspection_date ?? 0).getTime() -
                new Date(a.inspection_date ?? 0).getTime(),
            ),
        );

        setMaintenance(
          maintenanceRows.filter(
            (row: AnyRow) =>
              String(row.asset_code) === String(assetCode),
          ),
        );
      } catch (error) {
        console.error("SIMRAS report data load failed:", error);
      } finally {
        if (active) setLoading(false);
      }
    }

    load();

    return () => {
      active = false;
    };
  }, [assetCode]);

  const current = liveAsset ?? asset ?? {};
  const latestInspection = inspections[0];

  const dimensions =
    current?.dimensions &&
    typeof current.dimensions === "object" &&
    !Array.isArray(current.dimensions)
      ? current.dimensions
      : {};

  const dimensionEntries = Object.entries(dimensions);

  const health = Number(current.health_score);
  const risk = Number(current.risk_score);
  const rul = Number(current.rul_years);

  const type = String(
    current.asset_type ?? current.type ?? "UNKNOWN",
  ).toUpperCase();

  const defects = Array.isArray(latestInspection?.defects)
    ? latestInspection.defects
    : [];

  const currentAge = useMemo(() => {
    const built = Number(current.built_year);

    if (!Number.isFinite(built)) return "NOT AVAILABLE";

    return `${new Date().getFullYear() - built} years`;
  }, [current.built_year]);

  const downloadJson = () => {
    const payload = {
      asset: current,
      inspection_history: inspections,
      maintenance_history: maintenance,
      generated_at: new Date().toISOString(),
    };

    const blob = new Blob(
      [JSON.stringify(payload, null, 2)],
      { type: "application/json" },
    );

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = `${assetCode || "SIMRAS"}-inspection-report.json`;
    a.click();

    URL.revokeObjectURL(url);
  };

  const downloadCsv = () => {
    const rows = [
      ["Asset Code", show(assetCode)],
      ["Asset Name", show(current.name)],
      ["Type", show(type)],
      ["District", show(current.district)],
      ["Latitude", show(current.latitude)],
      ["Longitude", show(current.longitude)],
      ["Built Year", show(current.built_year)],
      ["Health Score", show(current.health_score)],
      ["Risk Score", show(current.risk_score)],
      ["Risk Level", show(current.risk_level)],
      ["RUL Years", show(current.rul_years)],
      ["Inspection Date", show(latestInspection?.inspection_date)],
      ["Inspection Condition", show(latestInspection?.condition_rating)],
      ["Inspection Findings", show(latestInspection?.findings)],
      ["Recommended Actions", show(latestInspection?.recommended_actions)],
      ["Source", show(current.source_url)],
    ];

    const escapeCsv = (value: any) =>
      `"${String(value).replace(/"/g, '""')}"`;

    const csv =
      "Field,Value\n" +
      rows
        .map(
          ([field, value]) =>
            `${escapeCsv(field)},${escapeCsv(value)}`,
        )
        .join("\n");

    const blob = new Blob([csv], {
      type: "text/csv;charset=utf-8",
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = `${assetCode || "SIMRAS"}-inspection-report.csv`;
    a.click();

    URL.revokeObjectURL(url);
  };

  return (
    <div
      id="simras-inspection-report"
      className="space-y-4"
    >
      <div className="bg-[#0B3B63] text-white rounded-lg p-5">
        <div className="flex flex-col lg:flex-row lg:justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-sky-200">
              Government of Andhra Pradesh • SIMRAS
            </div>

            <h1 className="text-xl font-bold mt-1">
              Infrastructure Inspection & Engineering Assessment
            </h1>

            <p className="text-sm text-sky-100 mt-1">
              {show(current.name)} • {show(assetCode)}
            </p>
          </div>

          <div className="flex flex-wrap gap-2 print:hidden">
            <button
              onClick={() => window.print()}
              className="bg-white text-[#0B3B63] px-3 py-2 rounded text-xs font-bold"
            >
              PDF
            </button>

            <button
              onClick={downloadCsv}
              className="bg-white text-[#0B3B63] px-3 py-2 rounded text-xs font-bold"
            >
              CSV
            </button>

            <button
              onClick={downloadJson}
              className="bg-white text-[#0B3B63] px-3 py-2 rounded text-xs font-bold"
            >
              JSON
            </button>
          </div>
        </div>
      </div>

      {loading && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 p-3 rounded text-sm">
          Loading live SIMRAS report data...
        </div>
      )}

      <Section number={1} title="Asset Identification">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <Field title="Asset Name" value={show(current.name)} />
          <Field title="Asset Code" value={show(assetCode)} />
          <Field title="Type" value={show(type)} />
          <Field title="District" value={show(current.district)} />
          <Field title="Latitude" value={show(current.latitude)} />
          <Field title="Longitude" value={show(current.longitude)} />
          <Field title="Built Year" value={show(current.built_year)} />
          <Field title="Current Age" value={currentAge} />
          <Field title="Material" value={show(current.material)} />
          <Field title="Condition" value={show(current.condition)} />
          <Field title="Authority" value={show(current.dimension_authority)} />
          <Field title="Identity Status" value={show(current.identity_status)} />
        </div>
      </Section>

      <Section number={2} title="Executive Inspection Summary">
        <div className="space-y-3 text-sm">
          <Field
            title="Latest Inspection"
            value={show(latestInspection?.inspection_date)}
          />

          <Field
            title="Inspection Condition"
            value={show(latestInspection?.condition_rating)}
          />

          <Field
            title="Findings"
            value={show(
              latestInspection?.findings,
              "No linked inspection record. No finding generated.",
            )}
          />
        </div>
      </Section>

      <Section number={3} title="Health Assessment">
        <div className="grid sm:grid-cols-3 gap-3">
          <Field
            title="Health Score"
            value={
              Number.isFinite(health)
                ? `${health.toFixed(1)} / 100`
                : "WITHHELD"
            }
          />

          <Field
            title="Condition"
            value={show(
              latestInspection?.condition_rating ?? current.condition,
            )}
          />

          <Field
            title="Assessment Basis"
            value={show(current.assessment_basis)}
          />
        </div>
      </Section>

      <Section number={4} title="Risk Assessment">
        <div className="grid sm:grid-cols-3 gap-3">
          <Field
            title="Risk Score"
            value={
              Number.isFinite(risk)
                ? `${risk.toFixed(1)} / 100`
                : "WITHHELD"
            }
          />

          <Field
            title="Risk Level"
            value={show(current.risk_level, "WITHHELD")}
          />

          <Field
            title="Evidence Basis"
            value={show(current.assessment_basis)}
          />
        </div>
      </Section>

      <Section number={5} title="Remaining Useful Life">
        <Field
          title="Estimated RUL"
          value={
            Number.isFinite(rul)
              ? `${rul.toFixed(1)} years`
              : "WITHHELD"
          }
        />
      </Section>

      <Section number={6} title="Inspection Findings">
        {latestInspection ? (
          <div className="space-y-3">
            <div className="grid sm:grid-cols-4 gap-3">
              <Field title="ID" value={show(latestInspection.id)} />
              <Field title="Inspector" value={show(latestInspection.inspector_name)} />
              <Field title="Type" value={show(latestInspection.inspection_type)} />
              <Field title="Status" value={show(latestInspection.status)} />
            </div>

            {defects.length > 0 ? (
              <div className="space-y-2">
                {defects.map((defect: AnyRow, index: number) => (
                  <div
                    key={index}
                    className="border border-slate-200 rounded p-3 text-sm"
                  >
                    <strong>{show(defect.component)}</strong>
                    <span className="ml-2 text-xs text-amber-700">
                      {show(defect.severity)}
                    </span>

                    <p className="mt-1 text-slate-600">
                      {show(defect.description)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">
                No defect entries recorded.
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            NO INSPECTION RECORD
          </p>
        )}
      </Section>

      <Section number={7} title="Engineering Dimensions">
        {dimensionEntries.length > 0 ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {dimensionEntries.map(([key, value]) => (
              <Field
                key={key}
                title={label(key)}
                value={show(value)}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-amber-700">
            ENGINEERING DIMENSIONS REQUIRED
          </p>
        )}
      </Section>

      <Section number={8} title={`${type} Specific Inspection`}>
        <Field
          title="Recorded Type-Specific Evidence"
          value={show(
            latestInspection?.findings,
            "No source-backed inspection finding linked.",
          )}
        />
      </Section>

      <Section number={9} title="Hydrology / Climate Evidence">
        <p className="text-sm text-slate-600">
          Values are displayed only where the selected asset API exposes
          current source-backed hydrology or environmental observations.
          Unsupported values remain withheld.
        </p>
      </Section>

      <Section number={10} title="AI / ML Assessment">
        <div className="grid sm:grid-cols-3 gap-3">
          <Field
            title="Health"
            value={Number.isFinite(health) ? health.toFixed(1) : "WITHHELD"}
          />

          <Field
            title="Risk"
            value={Number.isFinite(risk) ? risk.toFixed(1) : "WITHHELD"}
          />

          <Field
            title="RUL"
            value={Number.isFinite(rul) ? `${rul.toFixed(1)} years` : "WITHHELD"}
          />
        </div>
      </Section>

      <Section number={11} title="Government / Official Evidence">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <Field title="Identity Status" value={show(current.identity_status)} />
          <Field title="Dimension Status" value={show(current.dimension_status)} />
          <Field title="Fidelity Status" value={show(current.fidelity_status)} />
          <Field title="Authority" value={show(current.dimension_authority)} />
          <Field title="Source URL" value={show(current.source_url)} />
          <Field title="Assessment Basis" value={show(current.assessment_basis)} />
        </div>
      </Section>

      <Section number={12} title="Maintenance Recommendations">
        <Field
          title="Inspection Recommendation"
          value={show(latestInspection?.recommended_actions)}
        />

        <div className="mt-3 space-y-2">
          {maintenance.length > 0 ? (
            maintenance.map((row) => (
              <div
                key={row.id}
                className="border border-slate-200 rounded p-3 text-sm"
              >
                <strong>{show(row.title)}</strong>

                <div className="mt-1 text-slate-600">
                  {show(row.work_description)}
                </div>

                <div className="mt-2 text-xs">
                  Status: {show(row.status)} • Priority: {show(row.priority)}
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">
              No maintenance record linked.
            </p>
          )}
        </div>
      </Section>

      <Section number={13} title="Inspection History">
        {inspections.length > 0 ? (
          <div className="space-y-2">
            {inspections.map((row) => (
              <div
                key={row.id}
                className="border border-slate-200 rounded p-3 text-sm"
              >
                <strong>{show(row.id)}</strong>
                {" • "}
                {show(row.inspection_date)}
                {" • "}
                {show(row.condition_rating)}
                {" • "}
                {show(row.status)}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            No inspection history available.
          </p>
        )}
      </Section>

      <Section number={14} title="Evidence Gallery / Supporting Records">
        <p className="text-sm text-slate-600">
          Evidence files, photographs and drawings are shown only when
          actual attachment or media references are available from SIMRAS.
          No placeholder evidence is generated.
        </p>
      </Section>

      <Section number={15} title="Final Engineering Decision">
        <div className="grid sm:grid-cols-2 gap-3">
          <Field
            title="Inspection Status"
            value={show(latestInspection?.status, "WITHHELD")}
          />

          <Field
            title="Reviewed By"
            value={show(latestInspection?.reviewed_by)}
          />

          <Field
            title="Reviewer Comments"
            value={show(latestInspection?.reviewer_comments)}
          />

          <Field
            title="Reviewed At"
            value={show(latestInspection?.reviewed_at)}
          />
        </div>
      </Section>

      <Section number={16} title="Report Export & Transparency">
        <div className="grid sm:grid-cols-4 gap-3">
          <Field title="Asset Scope" value={show(assetCode)} />
          <Field title="Inspection Records" value={inspections.length} />
          <Field title="Maintenance Records" value={maintenance.length} />
          <Field title="Evidence Policy" value="NO UNSUPPORTED VALUES" />
        </div>
      </Section>
    </div>
  );
}
