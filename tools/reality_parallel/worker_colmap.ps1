param(
  [string]$ProjectRoot,
  [string]$LogRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $ProjectRoot

$log = Join-Path $LogRoot "COLMAP.log"
Start-Transcript -Path $log -Force | Out-Null

try {
    Write-Host "=== COLMAP WORKER ===" -ForegroundColor Cyan

    $toolRoot = Join-Path $ProjectRoot "tools\colmap"
    New-Item -ItemType Directory -Force $toolRoot | Out-Null

    $existing = Get-ChildItem $toolRoot -Recurse -Filter "COLMAP.bat" -File -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if($existing) {
        Write-Host "COLMAP already present: $($existing.FullName)" -ForegroundColor Green
        & $existing.FullName -h
        Set-Content (Join-Path $toolRoot "colmap_path.txt") $existing.FullName -Encoding utf8
        exit 0
    }

    $headers = @{
        "User-Agent" = "SIMRAS-RealityTwin/1.0"
        "Accept" = "application/vnd.github+json"
    }

    Write-Host "Querying latest official COLMAP GitHub release..."
    $release = Invoke-RestMethod "https://api.github.com/repos/colmap/colmap/releases/latest" -Headers $headers -TimeoutSec 120

    $windows = @($release.assets | Where-Object {
        $_.name -match "(?i)windows" -and $_.name -match "(?i)\.zip$"
    })

    if($windows.Count -eq 0) {
        throw "Latest COLMAP release contains no Windows ZIP asset."
    }

    $hasNvidia = $false
    try {
        nvidia-smi *> $null
        if($LASTEXITCODE -eq 0) { $hasNvidia = $true }
    } catch {}

    $chosen = $null
    if($hasNvidia) {
        $chosen = @($windows | Where-Object { $_.name -match "(?i)cuda" } | Select-Object -First 1)
        if($chosen.Count) { $chosen = $chosen[0] } else { $chosen = $null }
    }

    if($null -eq $chosen) {
        $cpu = @($windows | Where-Object { $_.name -notmatch "(?i)cuda" } | Select-Object -First 1)
        if($cpu.Count) { $chosen = $cpu[0] }
    }

    if($null -eq $chosen) {
        $chosen = $windows[0]
    }

    Write-Host "Release : $($release.tag_name)"
    Write-Host "Asset   : $($chosen.name)"
    Write-Host "NVIDIA  : $hasNvidia"

    $zip = Join-Path $toolRoot $chosen.name
    if(-not (Test-Path $zip)) {
        Write-Host "Downloading COLMAP..."
        Invoke-WebRequest $chosen.browser_download_url -OutFile $zip -Headers @{
            "User-Agent" = "SIMRAS-RealityTwin/1.0"
        } -TimeoutSec 1800
    }

    $extract = Join-Path $toolRoot "current"
    if(Test-Path $extract) {
        Remove-Item $extract -Recurse -Force
    }
    New-Item -ItemType Directory -Force $extract | Out-Null

    Write-Host "Extracting..."
    Expand-Archive $zip -DestinationPath $extract -Force

    $bat = Get-ChildItem $extract -Recurse -Filter "COLMAP.bat" -File -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if(-not $bat) {
        throw "COLMAP.bat not found after extraction."
    }

    Set-Content (Join-Path $toolRoot "colmap_path.txt") $bat.FullName -Encoding utf8

    Write-Host ""
    Write-Host "COLMAP PATH: $($bat.FullName)" -ForegroundColor Green
    & $bat.FullName -h
    if($LASTEXITCODE -ne 0) {
        throw "COLMAP command check failed."
    }

    Write-Host ""
    Write-Host "COLMAP_SETUP=PASS" -ForegroundColor Green
}
catch {
    Write-Host "COLMAP_SETUP=FAIL" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    throw
}
finally {
    Stop-Transcript | Out-Null
}