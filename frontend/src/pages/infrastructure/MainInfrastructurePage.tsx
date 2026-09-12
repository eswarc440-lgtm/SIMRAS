import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "../../services/api";

type Category =
  | "dam"
  | "barrage"
  | "bridge"
  | "road"
  | "airport"
  | "temple";

type AssetRecord = Record<string, unknown>;

const CATEGORY_ORDER: Category[] = [
  "dam",
  "barrage",
  "bridge",
  "road",
  "airport",
  "temple",
];

const CATEGORY_META: Record<
  Category,
  { title: string; subtitle: string }
> = {
  dam: {
    title: "Dams",
    subtitle: "Major dams and reservoir infrastructure",
  },

  barrage: {
    title: "Barrages",
    subtitle: "Major river regulation and barrage infrastructure",
  },

  bridge: {
    title: "Bridges",
    subtitle:
      "Major road bridges, railway bridges, flyovers and viaducts",
  },

  road: {
    title: "Roads",
    subtitle:
      "Major National Highways, State Highways and strategic road corridors",
  },

  airport: {
    title: "Airports",
    subtitle: "Major aviation infrastructure",
  },

  temple: {
    title: "Temples",
    subtitle: "Major heritage and pilgrimage infrastructure",
  },
};

const MAIN_MATCHERS: Record<Category, RegExp[]> = {
  dam: [
    /srisailam/i,
    /nagarjuna.*sagar/i,
    /somasila/i,
    /kandaleru/i,
    /polavaram/i,
    /gandikota/i,
    /velugodu/i,
    /yeleru/i,
    /gundlakamma/i,
    /veligonda/i,
    /tatipudi/i,
    /kalyani/i,
    /pedderu/i,
    /upper pennar/i,
    /yogi vemana/i,
    /maddileru/i,
  ],

  barrage: [
    /prakasam/i,
    /dowleswaram/i,
    /sir arthur cotton/i,
    /cotton barrage/i,
    /thotapalli/i,
    /gotta/i,
    /sangam/i,
    /penna barrage/i,
    /nellore barrage/i,
  ],

  bridge: [
    /godavari arch/i,
    /godavari.*bridge/i,
    /road.*cum.*rail/i,
    /havelock/i,
    /old godavari/i,
    /kanaka durga/i,
    /railway bridge/i,
    /rail bridge/i,
    /flyover/i,
    /viaduct/i,
  ],

  road: [
    /\bnh[\s-]?\d+/i,
    /national highway/i,
    /\bsh[\s-]?\d+/i,
    /state highway/i,
    /expressway/i,
    /ring road/i,
    /bypass/i,
    /major district road/i,
  ],

  airport: [
    /vijayawada/i,
    /tirupati/i,
    /rajahmundry/i,
    /rajamahendravaram/i,
    /kadapa/i,
    /cuddapah/i,
    /kurnool/i,
    /uyyalawada/i,
    /puttaparthi/i,
    /sri sathya sai/i,
    /bhogapuram/i,
    /alluri sitarama raju/i,
    /visakhapatnam/i,
  ],

  temple: [
    /tirumala/i,
    /venkateswara/i,
    /mallikarjuna/i,
    /kanaka durga/i,
    /simhachalam/i,
    /annavaram/i,
    /srikalahasti/i,
    /sri kalahasti/i,
    /kanipakam/i,
    /dwaraka tirumala/i,
    /mahanandi/i,
    /ahobilam/i,
    /lepakshi/i,
    /draksharamam/i,
    /amareswara/i,
    /mangalagiri/i,
    /panakala/i,
  ],
};

function value(
  object: AssetRecord,
  ...keys: string[]
): string {
  for (const key of keys) {
    const candidate = object[key];

    if (
      candidate !== null &&
      candidate !== undefined &&
      String(candidate).trim() !== ""
    ) {
      return String(candidate).trim();
    }
  }

  return "";
}

function assetType(
  asset: AssetRecord,
): Category | null {
  const raw = value(
    asset,
    "asset_type",
    "type",
    "infrastructure_type",
  ).toLowerCase();

  if (
    raw === "dam" ||
    raw === "barrage" ||
    raw === "bridge" ||
    raw === "road" ||
    raw === "airport" ||
    raw === "temple"
  ) {
    return raw;
  }

  return null;
}

function assetCode(asset: AssetRecord): string {
  return value(asset, "asset_code", "code", "id");
}

function assetName(asset: AssetRecord): string {
  return value(asset, "name", "asset_name", "title");
}

function extractAssets(
  payload: unknown,
): AssetRecord[] {
  if (Array.isArray(payload)) {
    return payload.filter(
      (item): item is AssetRecord =>
        typeof item === "object" &&
        item !== null,
    );
  }

  if (
    typeof payload === "object" &&
    payload !== null
  ) {
    const root =
      payload as Record<string, unknown>;

    for (const key of [
      "items",
      "assets",
      "data",
      "results",
    ]) {
      if (Array.isArray(root[key])) {
        return (
          root[key] as unknown[]
        ).filter(
          (item): item is AssetRecord =>
            typeof item === "object" &&
            item !== null,
        );
      }
    }
  }

  return [];
}

function isMainAsset(
  asset: AssetRecord,
  type: Category,
): boolean {
  const searchable = [
    assetName(asset),
    value(asset, "subtype"),
    value(asset, "road_class"),
    value(asset, "route_ref"),
    assetCode(asset),
  ].join(" ");

  return MAIN_MATCHERS[type].some(
    (pattern) => pattern.test(searchable),
  );
}

function AssetCard({
  asset,
}: {
  asset: AssetRecord;
}) {
  const type = assetType(asset);
  const code = assetCode(asset);
  const name = assetName(asset);

  const district =
    value(asset, "district", "region") ||
    "District not linked";

  const identity =
    value(asset, "identity_status") ||
    "NEEDS VERIFICATION";

  return (
    <article className="rounded-xl border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-primary">
            {type?.toUpperCase()}
          </p>

          <h3 className="mt-1 text-lg font-bold">
            {name || code}
          </h3>

          <p className="mt-1 text-xs text-muted-foreground">
            {code || "Canonical ID unavailable"}
          </p>
        </div>

        <span className="rounded-md border px-2 py-1 text-[10px] font-semibold">
          {identity}
        </span>
      </div>

      <div className="mt-4">
        <p className="text-xs text-muted-foreground">
          District
        </p>

        <p className="mt-1 text-sm font-medium">
          {district}
        </p>
      </div>

      {code ? (
        <div className="mt-5 flex flex-wrap gap-2">
          <a
            href={`/digital-twin?asset=${encodeURIComponent(
              code,
            )}`}
            className="rounded-md bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground"
          >
            Digital Twin
          </a>

          <a
            href={`/reports/${encodeURIComponent(
              code,
            )}`}
            className="rounded-md border px-3 py-2 text-xs font-semibold"
          >
            Report
          </a>

          <a
            href={`/gis?asset=${encodeURIComponent(
              code,
            )}`}
            className="rounded-md border px-3 py-2 text-xs font-semibold"
          >
            GIS
          </a>
        </div>
      ) : null}
    </article>
  );
}

export function MainInfrastructurePage() {
  const [assets, setAssets] = useState<
    AssetRecord[]
  >([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        let payload: unknown;

        try {
          payload =
            await apiRequest<unknown>(
              "/api/v1/assets?limit=5000",
            );
        } catch {
          payload =
            await apiRequest<unknown>(
              "/api/v1/assets",
            );
        }

        if (active) {
          setAssets(extractAssets(payload));
        }
      } catch (cause) {
        if (active) {
          setError(
            cause instanceof Error
              ? cause.message
              : "Unable to load infrastructure.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      active = false;
    };
  }, []);

  const grouped = useMemo(() => {
    const result: Record<
      Category,
      AssetRecord[]
    > = {
      dam: [],
      barrage: [],
      bridge: [],
      road: [],
      airport: [],
      temple: [],
    };

    const seen = new Set<string>();

    for (const asset of assets) {
      const type = assetType(asset);

      if (!type) continue;
      if (!isMainAsset(asset, type)) continue;

      const key =
        assetCode(asset) ||
        `${type}:${assetName(
          asset,
        ).toLowerCase()}`;

      if (seen.has(key)) continue;

      seen.add(key);
      result[type].push(asset);
    }

    for (const type of CATEGORY_ORDER) {
      result[type].sort((a, b) =>
        assetName(a).localeCompare(
          assetName(b),
        ),
      );
    }

    return result;
  }, [assets]);

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto max-w-[1600px] space-y-8 px-5 py-8 lg:px-8">

        <header className="rounded-xl border bg-card p-6">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">
            SIMRAS / ANDHRA PRADESH
          </p>

          <h1 className="mt-2 text-3xl font-bold">
            Main Infrastructure
          </h1>

          <p className="mt-2 max-w-4xl text-sm text-muted-foreground">
            Main Andhra Pradesh infrastructure
            with Roads and Bridges maintained as
            independent asset classes.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          {CATEGORY_ORDER.map((type) => (
            <div
              key={type}
              className="rounded-xl border bg-card p-5"
            >
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                {CATEGORY_META[type].title}
              </p>

              <p className="mt-3 text-3xl font-bold">
                {grouped[type].length}
              </p>

              <p className="mt-1 text-xs text-muted-foreground">
                Main assets
              </p>
            </div>
          ))}
        </section>

        {loading ? (
          <div className="rounded-xl border p-8">
            Loading infrastructure…
          </div>
        ) : null}

        {error ? (
          <div className="rounded-xl border p-5">
            {error}
          </div>
        ) : null}

        {!loading &&
          CATEGORY_ORDER.map((type) => (
            <section
              key={type}
              className="space-y-4"
            >
              <div className="border-b pb-3">
                <h2 className="text-xl font-bold">
                  {CATEGORY_META[type].title}
                </h2>

                <p className="mt-1 text-sm text-muted-foreground">
                  {
                    CATEGORY_META[type]
                      .subtitle
                  }
                </p>
              </div>

              {grouped[type].length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {grouped[type].map(
                    (asset, index) => (
                      <AssetCard
                        key={
                          assetCode(asset) ||
                          `${type}-${index}`
                        }
                        asset={asset}
                      />
                    ),
                  )}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
                  No canonical main{" "}
                  {
                    CATEGORY_META[type]
                      .title
                  }{" "}
                  asset is currently linked.
                </div>
              )}
            </section>
          ))}
      </div>
    </main>
  );
}

export default MainInfrastructurePage;
