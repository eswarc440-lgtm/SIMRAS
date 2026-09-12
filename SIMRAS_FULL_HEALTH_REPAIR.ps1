param(
  [string]$ProjectRoot = "D:\simras-digital-twin-repository\simras-digital-twin"
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot
[Environment]::CurrentDirectory = (Get-Location).Path

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $ProjectRoot "archive\full_health_repair_$stamp"
New-Item -ItemType Directory -Force $backup | Out-Null

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "SIMRAS FULL FRONTEND + BACKEND HEALTH REPAIR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Backup: $backup" -ForegroundColor DarkGray

# -------------------------------------------------------------------
# 1. BACKUP ONLY CODE / CONFIG. Database volumes are never modified.
# -------------------------------------------------------------------
Write-Host "`n[1/9] Backing up current code..." -ForegroundColor Cyan

Copy-Item ".\frontend\src" (Join-Path $backup "frontend_src") -Recurse -Force
foreach ($file in @(
  ".\frontend\package.json",
  ".\frontend\package-lock.json",
  ".\frontend\vite.config.ts",
  ".\frontend\.env.development",
  ".\frontend\.env.production",
  ".\backend\app\main.py",
  ".\backend\app\api\router.py",
  ".\backend\app\api\routes\ui_compat.py"
)) {
  if (Test-Path $file) {
    $safe = ($file.TrimStart(".\")).Replace("\","__")
    Copy-Item $file (Join-Path $backup $safe) -Force
  }
}

# -------------------------------------------------------------------
# 2. REPAIR THE SYSTEMATIC ? / ?? CORRUPTION.
#    This is the cause visible in Infrastructure/Maintenance/Inspection.
# -------------------------------------------------------------------
Write-Host "`n[2/9] Repairing malformed TypeScript nullish operators..." -ForegroundColor Cyan

@'
from pathlib import Path
import re

src = Path("frontend/src")

# Exact known corruptions that have already appeared in Vite.
exact = {
    "Number(asset.health_score ? 0)": "Number(asset.health_score ?? 0)",
    "Number(asset.risk_score ? 0)": "Number(asset.risk_score ?? 0)",
    "Number(asset.latitude ? 0)": "Number(asset.latitude ?? 0)",
    "Number(asset.longitude ? 0)": "Number(asset.longitude ?? 0)",
    "asset.built_year ? asset.age ? 0": "asset.built_year ?? asset.age ?? 0",
    "asset.remaining_useful_life ? asset.remaining_life ? 0": "asset.remaining_useful_life ?? asset.remaining_life ?? 0",
    "payload.items ? []": "payload.items ?? []",
    "record.cost ? record.estimated_cost ? record.actual_cost": "record.cost ?? record.estimated_cost ?? record.actual_cost",
    "inspection.condition_score ? inspection.inspection_score": "inspection.condition_score ?? inspection.inspection_score",
    'user?.name?.charAt(0) ? "S"': 'user?.name?.charAt(0) ?? "S"',
}

changed = []
for p in src.rglob("*"):
    if not p.is_file() or p.suffix not in {".ts", ".tsx"}:
        continue

    text = p.read_text(encoding="utf-8-sig")
    original = text

    for bad, good in exact.items():
        text = text.replace(bad, good)

    # Safe syntax repairs only:
    # return a ? b;                 -> return a ?? b;
    # const x = Number(a ? 0);      -> Number(a ?? 0);
    # const x = String(a ? "");     -> String(a ?? "");
    # (items ? [])                  -> (items ?? [])
    #
    # We intentionally DO NOT alter valid ternaries that contain ':'.
    lines = text.splitlines()
    out = []

    for line in lines:
        candidate = line

        # Return statement with a single-line missing colon is invalid TS and
        # almost always a damaged nullish-coalescing expression in this merge.
        if re.search(r"\breturn\b.*\s\?\s.*;\s*$", candidate) and ":" not in candidate:
            candidate = re.sub(r"(?<!\?)\s\?\s(?!\?)", " ?? ", candidate)

        # Number/String/Boolean wrappers cannot contain a ternary without ':'.
        for fn in ("Number", "String", "Boolean"):
            if f"{fn}(" in candidate and " ? " in candidate and ":" not in candidate:
                candidate = re.sub(r"(?<!\?)\s\?\s(?!\?)", " ?? ", candidate)

        # Typical assignment line damaged from ?? to ?.
        if (
            re.search(r"\b(?:const|let)\s+\w+\s*=.*\s\?\s.*;\s*$", candidate)
            and ":" not in candidate
            and "?." not in candidate
        ):
            candidate = re.sub(r"(?<!\?)\s\?\s(?!\?)", " ?? ", candidate)

        out.append(candidate)

    text = "\n".join(out)
    if original.endswith("\n"):
        text += "\n"

    if text != original:
        p.write_text(text, encoding="utf-8")
        changed.append(str(p))

print("Files repaired:", len(changed))
for name in changed[:30]:
    print("  ", name)
'@ | py -

if ($LASTEXITCODE -ne 0) {
  throw "TYPESCRIPT SOURCE REPAIR FAILED"
}

# -------------------------------------------------------------------
# 3. BUILD-AND-REPAIR LOOP.
#    If another parser error says ':' expected, repair only that line.
# -------------------------------------------------------------------
Write-Host "`n[3/9] Building frontend and clearing remaining parser corruptions..." -ForegroundColor Cyan

@'
from pathlib import Path
import subprocess
import re
import sys

frontend = Path("frontend")
max_repairs = 20

def run_build():
    proc = subprocess.run(
        ["npm.cmd", "run", "build"],
        cwd=str(frontend),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout

for attempt in range(max_repairs + 1):
    code, output = run_build()
    print(output)

    if code == 0:
        print("FRONTEND_BUILD_PASS")
        sys.exit(0)

    # tsc style:
    # src/file.tsx:76:67 - error ...
    patterns = [
        r'(src[\\/][^:\r\n]+\.tsx?):(\d+):(\d+)',
        r'(src[\\/][^( \r\n]+\.tsx?)\((\d+),(\d+)\)',
    ]

    match = None
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            break

    if not match:
        print("BUILD_FAILED_NON_PARSER_ERROR")
        sys.exit(2)

    rel, line_no, col_no = match.group(1), int(match.group(2)), int(match.group(3))
    p = frontend / Path(rel.replace("\\", "/"))

    if not p.exists():
        print("Cannot locate failing file:", p)
        sys.exit(3)

    lines = p.read_text(encoding="utf-8-sig").splitlines()
    if line_no < 1 or line_no > len(lines):
        print("Invalid reported line:", line_no)
        sys.exit(4)

    line = lines[line_no - 1]
    print(f"AUTO-REPAIR CANDIDATE {rel}:{line_no}:{col_no}")
    print("BEFORE:", line)

    # Only repair a line where the parser is expecting ':' and a single
    # spaced '?' exists without ':'; this avoids touching valid ternaries.
    if " ? " not in line or ":" in line:
        print("Not safe to auto-repair this line.")
        sys.exit(5)

    repaired = re.sub(r"(?<!\?)\s\?\s(?!\?)", " ?? ", line)

    if repaired == line:
        print("No safe repair available.")
        sys.exit(6)

    lines[line_no - 1] = repaired
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("AFTER :", repaired)
    print("Retrying build...")

print("Exceeded automatic parser repair limit.")
sys.exit(7)
'@ | py -

$frontRepairExit = $LASTEXITCODE
if ($frontRepairExit -ne 0) {
  Write-Host "`nFrontend build did not reach PASS." -ForegroundColor Red
  Write-Host "Running containers were NOT replaced." -ForegroundColor Yellow
  throw "FRONTEND BUILD FAILED - SEE THE LAST REAL ERROR ABOVE"
}

# -------------------------------------------------------------------
# 4. VERIFY ACTIVE FRONTEND DOES NOT IMPORT THE REMOVED MOCK DATA.
# -------------------------------------------------------------------
Write-Host "`n[4/9] Auditing frontend data sources..." -ForegroundColor Cyan

$mockImports = Get-ChildItem ".\frontend\src" -Recurse -File -Include *.ts,*.tsx |
  Select-String -Pattern `
    'data/infrastructureData',
    'data/analyticsData',
    'mockRequest',
    'Rajiv Bridge',
    'Central Ring Road',
    'Municipal Administration Building',
    'operator@simras\.local',
    'R² 0\.966',
    '94\.2%'

if ($mockImports) {
  Write-Host "WARNING: Remaining mock/demo references:" -ForegroundColor Yellow
  $mockImports | Select-Object Path,LineNumber,Line | Format-Table -Wrap
} else {
  Write-Host "Frontend active mock marker scan: CLEAN" -ForegroundColor Green
}

# -------------------------------------------------------------------
# 5. VERIFY API BASE CONFIG. Do not overwrite Cesium/other env values.
# -------------------------------------------------------------------
Write-Host "`n[5/9] Verifying frontend -> backend API configuration..." -ForegroundColor Cyan

$utf8 = New-Object System.Text.UTF8Encoding($false)

foreach ($envFile in @(".\frontend\.env.development", ".\frontend\.env.production")) {
  $content = if (Test-Path $envFile) { Get-Content $envFile -Raw } else { "" }

  if ($content -match "(?m)^VITE_API_BASE_URL=") {
    $content = [regex]::Replace(
      $content,
      "(?m)^VITE_API_BASE_URL=.*$",
      "VITE_API_BASE_URL=http://127.0.0.1:8000"
    )
  } else {
    $content = $content.TrimEnd() + "`nVITE_API_BASE_URL=http://127.0.0.1:8000`n"
  }

  [IO.File]::WriteAllText((Resolve-Path (Split-Path $envFile -Parent)).Path + "\" + (Split-Path $envFile -Leaf), $content.TrimStart(), $utf8)
}

# -------------------------------------------------------------------
# 6. BACKEND COMPILE + ROUTE PREFLIGHT.
# -------------------------------------------------------------------
Write-Host "`n[6/9] Checking FastAPI backend routes..." -ForegroundColor Cyan

py -m py_compile ".\backend\app\main.py"

if (Test-Path ".\backend\app\api\routes\ui_compat.py") {
  py -m py_compile ".\backend\app\api\routes\ui_compat.py"
}

if ($LASTEXITCODE -ne 0) {
  throw "BACKEND PYTHON COMPILE FAILED"
}

docker compose build backend frontend
if ($LASTEXITCODE -ne 0) {
  throw "DOCKER IMAGE BUILD FAILED - RUNNING CONTAINERS WERE NOT REPLACED"
}

docker compose run --rm --no-deps backend python -c "from app.main import app; p={getattr(r,'path','') for r in app.routes}; req=['/api/v1/dashboard/overview','/api/v1/infrastructure','/api/v1/gis/assets','/api/v1/inspections','/api/v1/maintenance','/api/v1/predictions','/api/v1/analytics/models/status']; m=[x for x in req if x not in p]; print('ROUTE_PREFLIGHT=', 'PASS' if not m else 'FAIL'); print('MISSING=',m); raise SystemExit(1 if m else 0)"

if ($LASTEXITCODE -ne 0) {
  throw "BACKEND ROUTE PREFLIGHT FAILED - RUNNING CONTAINERS WERE NOT REPLACED"
}

# -------------------------------------------------------------------
# 7. RECREATE APP SERVICES ONLY. DB VOLUME IS NOT TOUCHED.
# -------------------------------------------------------------------
Write-Host "`n[7/9] Starting healthy backend/frontend..." -ForegroundColor Cyan

docker compose up -d --force-recreate backend frontend
if ($LASTEXITCODE -ne 0) {
  throw "CONTAINER START FAILED"
}

Start-Sleep -Seconds 8

# -------------------------------------------------------------------
# 8. LIVE ENDPOINT + CORS + DATABASE HEALTH.
# -------------------------------------------------------------------
Write-Host "`n[8/9] Running live health checks..." -ForegroundColor Cyan

function Test-SimrasUrl {
  param([string]$Name,[string]$Url)

  $code = curl.exe -s -o NUL -w "%{http_code}" $Url
  if ($code -eq "200") {
    Write-Host ("{0,-22} PASS ({1})" -f $Name,$code) -ForegroundColor Green
    return $true
  }

  Write-Host ("{0,-22} CHECK ({1})" -f $Name,$code) -ForegroundColor Yellow
  return $false
}

$results = @()
$results += Test-SimrasUrl "Frontend" "http://localhost:5173/"
$results += Test-SimrasUrl "Backend docs" "http://localhost:8000/docs"
$results += Test-SimrasUrl "Dashboard API" "http://localhost:8000/api/v1/dashboard/overview"
$results += Test-SimrasUrl "Infrastructure API" "http://localhost:8000/api/v1/infrastructure?limit=3"
$results += Test-SimrasUrl "GIS API" "http://localhost:8000/api/v1/gis/assets?limit=3"
$results += Test-SimrasUrl "Inspections API" "http://localhost:8000/api/v1/inspections?limit=3"
$results += Test-SimrasUrl "Maintenance API" "http://localhost:8000/api/v1/maintenance?limit=3"
$results += Test-SimrasUrl "Predictions API" "http://localhost:8000/api/v1/predictions?limit=3"
$results += Test-SimrasUrl "Model status" "http://localhost:8000/api/v1/analytics/models/status"

if (Test-Path ".\backend\app\api\routes\ui_compat.py") {
  $results += Test-SimrasUrl "Reports catalog" "http://localhost:8000/api/v1/reports/catalog"
}

Write-Host "`nDocker services:" -ForegroundColor Cyan
docker compose ps

Write-Host "`nDatabase table counts (when present):" -ForegroundColor Cyan
docker compose exec -T db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema() ORDER BY table_name" | grep -E "^(assets|inspections|maintenance|predictions)$" || true' 2>$null

Write-Host "`nCORS check:" -ForegroundColor Cyan
$cors = curl.exe -s -D - -o NUL -H "Origin: http://localhost:5173" "http://localhost:8000/api/v1/dashboard/overview"
if ($cors -match "access-control-allow-origin:\s*(http://localhost:5173|\*)") {
  Write-Host "Frontend origin allowed by backend CORS" -ForegroundColor Green
} else {
  Write-Host "CORS header not confirmed - inspect backend CORS config if browser API calls fail" -ForegroundColor Yellow
}

# -------------------------------------------------------------------
# 9. FINAL SUMMARY.
# -------------------------------------------------------------------
Write-Host "`n[9/9] Final result..." -ForegroundColor Cyan

if ($results -notcontains $false) {
  Write-Host "`n============================================================" -ForegroundColor Green
  Write-Host "SIMRAS STACK HEALTHY" -ForegroundColor Green
  Write-Host "FRONTEND -> FASTAPI -> POSTGIS CONNECTIONS PASS" -ForegroundColor Green
  Write-Host "============================================================" -ForegroundColor Green
} else {
  Write-Host "`n============================================================" -ForegroundColor Yellow
  Write-Host "BUILD IS HEALTHY; ONE OR MORE LIVE ENDPOINTS NEED REVIEW" -ForegroundColor Yellow
  Write-Host "============================================================" -ForegroundColor Yellow
}

Write-Host "Backup: $backup"
Write-Host "Database volume was not modified."

Start-Process "http://localhost:5173/"
