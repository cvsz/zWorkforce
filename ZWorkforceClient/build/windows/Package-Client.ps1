[CmdletBinding()]
param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [ValidateSet("x64", "ARM64")]
    [string]$Platform = "x64"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$appProject = Join-Path $root "src\ZWorkforceClient\ZWorkforceClient.csproj"
$output = Join-Path $root "out\$Configuration-$Platform"

New-Item -ItemType Directory -Force -Path $output | Out-Null

$publishArguments = @(
    "publish", $appProject,
    "--configuration", $Configuration,
    "--property:Platform=$Platform",
    "--property:RuntimeIdentifier=win-$($Platform.ToLowerInvariant())",
    "--property:GenerateAppxPackageOnBuild=true",
    "--property:AppxBundle=Never",
    "--property:AppxPackageDir=$output\",
    "--no-restore"
)
& dotnet @publishArguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$packages = @(Get-ChildItem -Path $root -Recurse -File -Include *.msix,*.msixbundle,*.cer | Where-Object { $_.FullName -notmatch '\\obj\\' })
if ($packages.Count -eq 0) {
    throw "The publish completed without producing an MSIX artifact."
}

foreach ($package in $packages) {
    Copy-Item -LiteralPath $package.FullName -Destination $output -Force
}

Write-Host "Windows client package artifacts:"
$packages | ForEach-Object { Write-Host "  $($_.FullName)" }
