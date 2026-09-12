param(
  [string]$ProjectRoot,
  [string]$LogRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $ProjectRoot

$log = Join-Path $LogRoot "REALITY_QUEUE.log"
Start-Transcript -Path $log -Force | Out-Null

try {
    Write-Host "=== REALITY TWIN QUEUE WORKER ===" -ForegroundColor Cyan

    $response = Invoke-RestMethod "http://localhost:8000/api/v1/assets?limit=1000" -TimeoutSec 120
    $items = if($null -ne $response.items){@($response.items)}
             elseif($null -ne $response.assets){@($response.assets)}
             else{@($response)}

    if($items.Count -eq 0) {
        throw "Assets API returned no items."
    }

    $showcaseNames = @(
        "Kanaka Durga",
        "Venkateswara",
        "Simhachalam",
        "Srikalahasti",
        "Mallikarjuna",
        "Annavaram",
        "Dwaraka Tirumala",
        "Godavari",
        "Prakasam",
        "Polavaram",
        "Somasila",
        "Srisailam",
        "Vijayawada Airport",
        "Tirupati Airport",
        "Visakhapatnam Airport"
    )

    function Priority([object]$a) {
        $name = [string]$a.name
        foreach($s in $showcaseNames) {
            if($name -like "*$s*") { return 1 }
        }
        switch([string]$a.asset_type) {
            "temple"  { return 2 }
            "bridge"  { return 2 }
            "barrage" { return 3 }
            "airport" { return 3 }
            "dam"     { return 4 }
            default   { return 5 }
        }
    }

    $queue = foreach($a in $items) {
        [pscustomobject]@{
            priority = Priority $a
            asset_code = $a.asset_code
            name = $a.name
            asset_type = $a.asset_type
            district = $a.district
            identity_status = $a.identity_status
            reality_pack = "data\reality_twin\$($a.asset_code)"
            imagery_status = if(Test-Path (Join-Path $ProjectRoot "data\reality_twin\$($a.asset_code)\imagery")){"STARTED"}else{"NOT_STARTED"}
            model_status = "NOT_AUDITED"
        }
    }

    $queue = @($queue | Sort-Object priority,asset_type,name)

    $outRoot = Join-Path $ProjectRoot "data\reality_twin"
    New-Item -ItemType Directory -Force $outRoot | Out-Null

    $queuePath = Join-Path $outRoot "reality_twin_queue.csv"
    $queue | Export-Csv $queuePath -NoTypeInformation -Encoding utf8

    # Create only metadata folders for high-priority assets. No downloads.
    foreach($row in @($queue | Where-Object {$_.priority -le 2})) {
        $root = Join-Path $ProjectRoot $row.reality_pack
        New-Item -ItemType Directory -Force `
            (Join-Path $root "imagery"), `
            (Join-Path $root "manifests"), `
            (Join-Path $root "reconstruction"), `
            (Join-Path $root "review") | Out-Null
    }

    # Create a deduplicated airport planning list by normalized name only.
    # This does NOT modify the canonical database.
    $airports = @($items | Where-Object {$_.asset_type -eq "airport"})
    $airportPlan = @(
        $airports |
        Group-Object { ([string]$_.name).Trim().ToLowerInvariant() } |
        ForEach-Object {
            $rows = @($_.Group | Sort-Object asset_code)
            [pscustomobject]@{
                airport_name = $rows[0].name
                canonical_candidates = ($rows.asset_code -join " | ")
                duplicate_count = $rows.Count
                action = if($rows.Count -gt 1){"REVIEW_ALIAS_MERGE"}else{"KEEP"}
            }
        } |
        Sort-Object airport_name
    )

    $airportPlan |
        Export-Csv (Join-Path $outRoot "airport_alias_review.csv") -NoTypeInformation -Encoding utf8

    Write-Host ""
    Write-Host "=== TOP REALITY TWIN QUEUE ===" -ForegroundColor Cyan
    $queue |
        Select-Object -First 30 priority,asset_code,name,asset_type,district,imagery_status |
        Format-Table -AutoSize -Wrap

    Write-Host ""
    Write-Host "=== AIRPORT ALIAS REVIEW ===" -ForegroundColor Cyan
    $airportPlan | Format-Table -AutoSize -Wrap

    Write-Host ""
    Write-Host "Queue: $queuePath" -ForegroundColor Green
    Write-Host "REALITY_QUEUE=PASS" -ForegroundColor Green
}
catch {
    Write-Host "REALITY_QUEUE=FAIL" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    throw
}
finally {
    Stop-Transcript | Out-Null
}