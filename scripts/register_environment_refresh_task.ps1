[CmdletBinding()]
param(
    [string]$TaskName = "SIMRAS Daily Environment Refresh",
    [string]$DailyAt = "06:30"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $PSScriptRoot "run_environment_refresh.ps1"
if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
    throw "Environment refresh runner was not found: $Runner"
}

try {
    $ScheduledTime = [datetime]::Today.Add([timespan]::ParseExact($DailyAt, "hh\:mm", $null))
}
catch {
    throw "DailyAt must use 24-hour HH:mm format, for example 06:30"
}

$PowerShell = (Get-Command powershell.exe -ErrorAction Stop).Source
$Arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$Runner`" -ProjectRoot `"$ProjectRoot`""
$Action = New-ScheduledTaskAction -Execute $PowerShell -Argument $Arguments -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At $ScheduledTime
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Downloads, validates, transforms, and loads SIMRAS environmental feeds." `
    -Force | Out-Null

$Task = Get-ScheduledTask -TaskName $TaskName
$Info = Get-ScheduledTaskInfo -TaskName $TaskName
[PSCustomObject]@{
    TaskName = $Task.TaskName
    State = $Task.State
    NextRunTime = $Info.NextRunTime
    LastRunTime = $Info.LastRunTime
    LastTaskResult = $Info.LastTaskResult
    Runner = $Runner
}
