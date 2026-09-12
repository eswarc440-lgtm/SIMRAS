param(
    [string]$ProjectRoot,
    [int]$FrontendPort = 5173,
    [int]$BackendPort = 8000,
    [string]$LogFile,
    [string]$ViteLog
)

$ErrorActionPreference = "Continue"
Set-Location $ProjectRoot

function Log([string]$Message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $Message"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function PortListening([int]$Port) {
    try {
        return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    } catch {
        return $false
    }
}

function ApiReady {
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:$BackendPort/api/v1/assets?limit=1" `
            -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function DockerReady {
    try {
        docker info *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function StartDocker {
    if(DockerReady){ return $true }

    $dd = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if(-not(Test-Path $dd)){
        $dd = Join-Path $env:LOCALAPPDATA "Programs\Docker\Docker\Docker Desktop.exe"
    }

    if(-not(Test-Path $dd)){
        Log "ERROR Docker Desktop.exe not found."
        return $false
    }

    Log "Starting Docker Desktop..."
    Start-Process $dd -ErrorAction SilentlyContinue | Out-Null

    for($i=0;$i -lt 90;$i++){
        Start-Sleep -Seconds 2
        if(DockerReady){
            Log "Docker engine READY."
            return $true
        }
    }

    Log "ERROR Docker engine did not become ready."
    return $false
}

function StartBackend {
    if(ApiReady){ return $true }

    if(-not(StartDocker)){ return $false }

    # Never launch old heavy generation containers.
    try {
        $heavy = @(
            docker ps -a --format "{{.Names}}" |
            Where-Object { $_ -match '^simras-v14-|^simras-v15-|osm2world|colmap' }
        )
        foreach($name in $heavy){
            if($name){
                docker rm -f $name *> $null
                Log "Removed obsolete heavy container: $name"
            }
        }
    } catch {}

    Log "Starting only PostGIS + FastAPI backend..."
    docker compose up -d db backend *> $null

    for($i=0;$i -lt 60;$i++){
        Start-Sleep -Seconds 2
        if(ApiReady){
            Log "Backend API READY."
            return $true
        }
    }

    Log "ERROR Backend API did not become ready."
    try {
        docker compose logs backend --tail=60 | Add-Content -Path $LogFile -Encoding UTF8
    } catch {}
    return $false
}

function StartFrontend {
    if(PortListening $FrontendPort){ return $true }

    $frontend = Join-Path $ProjectRoot "frontend"
    if(-not(Test-Path (Join-Path $frontend "package.json"))){
        Log "ERROR frontend package.json not found."
        return $false
    }

    Log "Starting Vite frontend on port $FrontendPort..."

    $cmd = @"
Set-Location '$frontend'
`$env:BROWSER='none'
npm run dev -- --host 0.0.0.0 --port $FrontendPort --strictPort 2>&1 | Tee-Object -FilePath '$ViteLog'
"@

    $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))

    Start-Process powershell.exe `
        -ArgumentList "-NoProfile","-EncodedCommand",$enc `
        -WindowStyle Hidden | Out-Null

    for($i=0;$i -lt 40;$i++){
        Start-Sleep -Seconds 1
        if(PortListening $FrontendPort){
            Log "Vite frontend READY."
            return $true
        }
    }

    Log "ERROR Vite frontend did not start."
    return $false
}

Log "SIMRAS runtime watchdog started. PID=$PID"

# Initial recovery
[void](StartFrontend)
[void](StartBackend)

while($true){
    try {
        if(-not(PortListening $FrontendPort)){
            Log "Frontend offline; recovering."
            [void](StartFrontend)
        }

        if(-not(ApiReady)){
            Log "Backend API offline; recovering."
            [void](StartBackend)
        }
    } catch {
        Log "WATCHDOG ERROR: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds 20
}