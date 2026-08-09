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
$pfxPath = Join-Path $output "zworkforce-client-temporary.pfx"
$cerPath = Join-Path $output "zworkforce-client-temporary.cer"

New-Item -ItemType Directory -Force -Path $output | Out-Null

$certificate = $null
try {
    Remove-Item -LiteralPath $pfxPath, $cerPath -Force -ErrorAction SilentlyContinue
    $certificate = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=cvsz" `
        -FriendlyName "zWorkforce Client temporary package signing" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -KeyExportPolicy Exportable `
        -NotAfter (Get-Date).AddDays(7)
    $certificatePassword = [Guid]::NewGuid().ToString("N")
    $secureCertificatePassword = ConvertTo-SecureString $certificatePassword -AsPlainText -Force
    Export-PfxCertificate -Cert $certificate -FilePath $pfxPath -Password $secureCertificatePassword | Out-Null
    Export-Certificate -Cert $certificate -FilePath $cerPath | Out-Null

    $publishArguments = @(
        "publish", $appProject,
        "--configuration", $Configuration,
        "--property:Platform=$Platform",
        "--property:RuntimeIdentifier=win-$($Platform.ToLowerInvariant())",
        "--property:WindowsAppSDKSelfContained=true",
        "--property:SelfContained=true",
        "--property:GenerateAppxPackageOnBuild=true",
        "--property:AppxPackageSigningEnabled=true",
        "--property:PackageCertificateKeyFile=$pfxPath",
        "--property:PackageCertificatePassword=$certificatePassword",
        "--property:PackageCertificateThumbprint=$($certificate.Thumbprint)",
        "--property:AppxBundle=Never",
        "--property:AppxPackageDir=$output\",
        "--no-restore"
    )
    & dotnet @publishArguments
    if ($LASTEXITCODE -ne 0) { throw "The packaged client publish failed with exit code $LASTEXITCODE." }
}
finally {
    if ($null -ne $certificate) {
        Remove-Item -LiteralPath "Cert:\CurrentUser\My\$($certificate.Thumbprint)" -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $pfxPath -Force -ErrorAction SilentlyContinue
}

$packages = @(Get-ChildItem -Path $root -Recurse -File -Include *.msix,*.msixbundle,*.cer | Where-Object { $_.FullName -notmatch '\\obj\\' })
if ($packages.Count -eq 0) {
    throw "The publish completed without producing an MSIX artifact."
}

foreach ($package in $packages) {
    $destination = Join-Path $output $package.Name
    if ([IO.Path]::GetFullPath($package.FullName) -ne [IO.Path]::GetFullPath($destination)) {
        Copy-Item -LiteralPath $package.FullName -Destination $destination -Force
    }
}

Write-Host "Windows client package artifacts:"
$packages | ForEach-Object { Write-Host "  $($_.FullName)" }
