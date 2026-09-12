from pathlib import Path

path = Path("/repo/frontend/src/App.tsx")
src = path.read_text(encoding="utf-8-sig")


import_line = (
    'import BridgeEngineeringViewer '
    'from "./features/digital-twin/BridgeEngineeringViewer";'
)

if import_line not in src:

    lines = src.splitlines()

    insert_at = 0

    for i, line in enumerate(lines):

        if line.startswith("import "):
            insert_at = i + 1

    lines.insert(
        insert_at,
        import_line,
    )

    src = "\n".join(lines) + "\n"


old = (
    '<RealityTwinAssetViewer '
    'assetCode={selected?.asset_code} />'
)

new = '''{selected?.asset_code?.startsWith("AP_BR_") ? (
                    <BridgeEngineeringViewer
                      assetCode={selected.asset_code}
                    />
                  ) : (
                    <RealityTwinAssetViewer
                      assetCode={selected?.asset_code}
                    />
                  )}'''


if old in src:

    src = src.replace(
        old,
        new,
        1,
    )

elif "BridgeEngineeringViewer" not in src[
    src.find("twin-stage"):
]:

    raise RuntimeError(
        "RealityTwinAssetViewer render line not found"
    )


path.write_text(
    src,
    encoding="utf-8",
    newline="\n",
)

print(
    "[PATCHED] App.tsx bridge-specific viewer routing"
)