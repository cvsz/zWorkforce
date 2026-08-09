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
    $packageDirectory = Join-Path $root "out\$Configuration-x64"
    $package = Get-ChildItem -LiteralPath $packageDirectory -File -Filter "*.msix" |
        Sort-Object LastWriteTimeUtc |
        Select-Object -Last 1
    if ($null -eq $package) {
        throw "The packaged launch smoke check requires an MSIX under $packageDirectory. Run Package-Client.ps1 first."
    }

    $certificate = Get-ChildItem -LiteralPath $packageDirectory -File -Filter "*.cer" |
        Sort-Object LastWriteTimeUtc |
        Select-Object -Last 1
    $importedCertificateThumbprint = $null
    $installedPackage = $null
    try {
        Get-AppxPackage -Name "cvsz.ZWorkforceClient" -ErrorAction SilentlyContinue |
            ForEach-Object { Remove-AppxPackage -Package $_.PackageFullName -ErrorAction SilentlyContinue }

        if ($null -ne $certificate) {
            $trustedCertificate = Get-ChildItem -Path "Cert:\CurrentUser\Root" |
                Where-Object Thumbprint -eq $certificate.Thumbprint |
                Select-Object -First 1
            if ($null -eq $trustedCertificate) {
                Import-Certificate -FilePath $certificate.FullName -CertStoreLocation "Cert:\CurrentUser\Root" | Out-Null
                $importedCertificateThumbprint = $certificate.Thumbprint
            }
        }

        Add-AppxPackage -Path $package.FullName -ForceApplicationShutdown -ErrorAction Stop
        $installedPackage = Get-AppxPackage -Name "cvsz.ZWorkforceClient" |
            Sort-Object Version -Descending |
            Select-Object -First 1
        if ($null -eq $installedPackage) {
            throw "The MSIX installed without a discoverable cvsz.ZWorkforceClient package."
        }

        $appShellId = "shell:AppsFolder\$($installedPackage.PackageFamilyName)!App"
        Start-Process -FilePath "explorer.exe" -ArgumentList $appShellId | Out-Null
        Start-Sleep -Seconds 8
        $process = Get-Process -Name "ZWorkforceClient" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($null -eq $process) {
            throw "The packaged client did not remain running after launch."
        }
        Write-Host "Windows client launch smoke check is alive (PID $($process.Id))."
    } finally {
        Get-Process -Name "ZWorkforceClient" -ErrorAction SilentlyContinue |
            Stop-Process -Force -ErrorAction SilentlyContinue
        if ($null -ne $installedPackage) {
            Remove-AppxPackage -Package $installedPackage.PackageFullName -ErrorAction SilentlyContinue
        }
        if ($null -ne $importedCertificateThumbprint) {
            Remove-Item -LiteralPath "Cert:\CurrentUser\Root\$importedCertificateThumbprint" -Force -ErrorAction SilentlyContinue
        }
    }
}
