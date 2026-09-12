import React, { useMemo } from "react";

type OpenPublicRealityTwinProps = {
  assetCode?: string | null;
};

export function OpenPublicRealityTwin({
  assetCode,
}: OpenPublicRealityTwinProps) {
  const src = useMemo(() => {
    const params = new URLSearchParams();

    if (assetCode) {
      params.set("asset", assetCode);
    }

    params.set("embedded", "1");

    return `/reality-twin/index.html?${params.toString()}`;
  }, [assetCode]);

  return (
    <div
      data-simras-reality-twin="true"
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        minHeight: "620px",
        overflow: "hidden",
        borderRadius: "10px",
        background: "#07111b",
      }}
    >
      <iframe
        key={assetCode ?? "no-asset"}
        title="SIMRAS Reality Twin"
        src={src}
        loading="eager"
        referrerPolicy="no-referrer"
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          minWidth: "100%",
          minHeight: "100%",
          display: "block",
          border: 0,
          margin: 0,
          padding: 0,
          background: "#07111b",
        }}
      />
    </div>
  );
}

export default OpenPublicRealityTwin;