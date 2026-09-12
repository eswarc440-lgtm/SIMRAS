[CmdletBinding()]
param(
    [string]$ProjectRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
$ComposeFile = Join-Path $ProjectRoot "compose.yml"
if (-not (Test-Path -LiteralPath $ComposeFile -PathType Leaf)) {
    throw "compose.yml was not found under $ProjectRoot"
}

$LogDirectory = Join-Path $ProjectRoot "data\logs"
$LockPath = Join-Path $LogDirectory "environment-refresh.lock"
$LogPath = Join-Path $LogDirectory "environment-refresh.log"
$StdOutPath = Join-Path $LogDirectory "environment-refresh.stdout.tmp"
$StdErrPath = Join-Path $LogDirectory "environment-refresh.stderr.tmp"
New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null

$Lock = $null
try {
    try {
        $Lock = [IO.File]::Open(
            $LockPath,
            [IO.FileMode]::OpenOrCreate,
            [IO.FileAccess]::ReadWrite,
            [IO.FileShare]::None
        )
    }
    catch [IO.IOException] {
        Write-Output "SIMRAS environment refresh is already running."
        exit 0
    }

    Set-Location -LiteralPath $ProjectRoot
    $StartedAt = Get-Date
    "[$($StartedAt.ToString('o'))] Starting SIMRAS environment refresh" |
        Tee-Object -FilePath $LogPath -Append

    $PythonCode = "import asyncio,json; from simras_etl.flows import environment_refresh; result=asyncio.run(environment_refresh()); print(json.dumps(result,indent=2,default=str))"
    # Start-Process keeps normal Docker stderr out of PowerShell's error stream.
    $QuotedPythonCode = '"' + $PythonCode.Replace('"', '\"') + '"'
    $DockerArguments = @(
        "compose", "--ansi", "never", "--profile", "etl", "run", "--rm",
        "-e", "DO_NOT_TRACK=1",
        "-e", "PREFECT_SERVER_ANALYTICS_ENABLED=false",
        "etl", "python", "-c", $QuotedPythonCode
    )
    $DockerProcess = Start-Process `
        -FilePath (Get-Command docker.exe -ErrorAction Stop).Source `
        -ArgumentList $DockerArguments `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $StdOutPath `
        -RedirectStandardError $StdErrPath
    $DockerExitCode = $DockerProcess.ExitCode
    foreach ($OutputPath in @($StdOutPath, $StdErrPath)) {
        if (Test-Path -LiteralPath $OutputPath -PathType Leaf) {
            Get-Content -LiteralPath $OutputPath |
                Tee-Object -FilePath $LogPath -Append
        }
    }
    if ($DockerExitCode -ne 0) {
        throw "Environment refresh failed with Docker exit code $DockerExitCode"
    }

    $FinishedAt = Get-Date
    "[$($FinishedAt.ToString('o'))] Completed SIMRAS environment refresh in $([math]::Round(($FinishedAt - $StartedAt).TotalSeconds, 1)) seconds" |
        Tee-Object -FilePath $LogPath -Append
}
catch {
    "[$((Get-Date).ToString('o'))] FAILED: $($_.Exception.Message)" |
        Tee-Object -FilePath $LogPath -Append
    throw
}
finally {
    if ($null -ne $Lock) {
        $Lock.Dispose()
    }
    Remove-Item -LiteralPath $StdOutPath -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $StdErrPath -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $LockPath -ErrorAction SilentlyContinue
}
