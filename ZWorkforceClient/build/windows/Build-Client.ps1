[CmdletBinding()]
param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [ValidateSet("x64", "ARM64")]
    [string]$Platform = "x64",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$solution = Join-Path $root "ZWorkforceClient.sln"

if ($Clean) {
    & dotnet clean $solution --configuration $Configuration --property:Platform=$Platform
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& dotnet restore $solution
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& dotnet build $solution --configuration $Configuration --property:Platform=$Platform --no-restore
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Windows client build completed: $Configuration/$Platform"
