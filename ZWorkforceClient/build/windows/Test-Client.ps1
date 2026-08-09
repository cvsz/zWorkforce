[CmdletBinding()]
param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [switch]$LaunchSmoke
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$solution = Join-Path $root "ZWorkforceClient.sln"
$appProject = Join-Path $root "src\ZWorkforceClient\ZWorkforceClient.csproj"

& dotnet test $solution --configuration $Configuration --property:Platform=x64 --no-restore
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($LaunchSmoke) {
    $arguments = @(
        "run",
        "--project", $appProject,
        "--configuration", $Configuration,
        "--property:Platform=x64",
        "--no-restore",
        "--no-build"
    )
    $process = Start-Process -FilePath "dotnet" -ArgumentList $arguments -PassThru -WindowStyle Hidden
    try {
        Start-Sleep -Seconds 8
        if ($process.HasExited) {
            throw "The client launch process exited with code $($process.ExitCode)."
        }
        Write-Host "Windows client launch smoke check is alive (PID $($process.Id))."
    } finally {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
