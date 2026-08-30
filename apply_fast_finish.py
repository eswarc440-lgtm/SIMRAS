from pathlib import Path

app_path = Path("frontend/src/App.tsx")
evidence_path = Path(
    "frontend/src/features/digital-twin/EvidenceStatePanel.tsx"
)

app = app_path.read_text(encoding="utf-8")

# Ensure TwinPanels import exists.
if 'from "./features/digital-twin/TwinPanels"' not in app:
    evidence_import = (
        'import { EvidenceStatePanel } '
        'from "./features/digital-twin/EvidenceStatePanel";'
    )
    twin_import = (
        'import { TwinPanels } '
        'from "./features/digital-twin/TwinPanels";'
    )

    if evidence_import in app:
        app = app.replace(
            evidence_import,
            evidence_import + "\n" + twin_import,
            1,
        )
    else:
        cesium_import = (
            'import { CesiumTwinViewer } '
            'from "./features/digital-twin/CesiumTwinViewer";'
        )
        app = app.replace(
            cesium_import,
            cesium_import + "\n" + twin_import,
            1,
        )

# Remove existing TwinPanels render so we can place it consistently.
app = app.replace(
    "\n                <TwinPanels twin={twin} />",
    "",
)

# Put prediction cards immediately after the 3D stage and BEFORE
# the official evidence layer.
evidence_marker = "\n                {evidenceState ? ("

if evidence_marker in app:
    app = app.replace(
        evidence_marker,
        "\n                <TwinPanels twin={twin} />"
        + evidence_marker,
        1,
    )
else:
    # Fallback for App versions without EvidenceStatePanel:
    # locate the twin stage and insert after its closing div.
    stage_marker = '<div className="twin-stage">'
    stage_start = app.find(stage_marker)

    if stage_start == -1:
        raise RuntimeError(
            "Could not locate the Digital Twin stage in frontend/src/App.tsx"
        )

    closing = app.find("</div>", stage_start)

    if closing == -1:
        raise RuntimeError(
            "Could not locate the Digital Twin stage closing div"
        )

    closing += len("</div>")
    app = (
        app[:closing]
        + "\n                <TwinPanels twin={twin} />"
        + app[closing:]
    )

app_path.write_text(app, encoding="utf-8")

# Make the evidence card clearly separate from the SIMRAS prediction layer.
if evidence_path.exists():
    evidence = evidence_path.read_text(encoding="utf-8")
    evidence = evidence.replace(
        "No fabricated health percentage",
        "Official evidence layer; SIMRAS prediction shown separately",
    )
    evidence_path.write_text(evidence, encoding="utf-8")

print("App patched: prediction panel is now before official evidence.")
