[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$requiredFailures = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

function Add-Failure([string]$Message) {
    $requiredFailures.Add($Message)
}

function Add-Warning([string]$Message) {
    $warnings.Add($Message)
}

function Get-CommandPath([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) { return $null }
    return $command.Source
}

if ($Install -and $CheckOnly) {
    throw "Choose either -Install or -CheckOnly, not both."
}

$os = Get-CimInstance Win32_OperatingSystem
$build = [int]$os.BuildNumber
$osLabel = "$($os.Caption) build $build"
if ($build -lt 22621) {
    Add-Failure "Windows 11 22H2/build 22621 or newer is required; found $osLabel."
}

$dotnetPath = Get-CommandPath "dotnet"
$dotnetVersion = $null
if ($null -eq $dotnetPath) {
    Add-Failure ".NET SDK 10 is missing. Install the .NET 10 SDK and restart the terminal."
} else {
    $dotnetVersion = (& dotnet --version).Trim()
    $major = [int]($dotnetVersion.Split('.')[0])
    if ($major -lt 10) {
        Add-Failure ".NET 10 SDK is required; found $dotnetVersion."
    }
}

$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
$vsPath = $null
if (Test-Path $vswhere) {
    $vsPath = (& $vswhere -latest -products * -requires Microsoft.VisualStudio.ComponentGroup.WindowsAppDevelopment -property installationPath 2>$null | Select-Object -First 1)
}
$sdkRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\Include"
$sdkVersions = @()
if (Test-Path $sdkRoot) {
    $sdkVersions = @(Get-ChildItem $sdkRoot -Directory | Where-Object { $_.Name -match '^10\.0\.\d+\.\d+$' } | Select-Object -ExpandProperty Name)
}
if (-not ($sdkVersions | Where-Object { [version]$_ -ge [version]'10.0.26100.0' })) {
    Add-Failure "Windows SDK 10.0.26100.0 or newer is missing."
}

$devMode = 0
try {
    $devMode = (Get-ItemPropertyValue -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" -Name AllowDevelopmentWithoutDevLicense -ErrorAction Stop)
} catch {
    $devMode = 0
}
if ($devMode -ne 1) {
    Add-Warning "Developer Mode is disabled. Enable it for local package deployment and launch verification."
}

$templateOutput = if ($null -ne $dotnetPath) { (& dotnet new list winui 2>&1 | Out-String) } else { "" }
if ($templateOutput -notmatch '(?i)winui') {
    Add-Failure "The WinUI dotnet template is missing. Verify the Visual Studio workload, restart the terminal, and run: dotnet new list winui"
}

$cliToolchainReady = $null -ne $dotnetPath -and
    $null -ne $dotnetVersion -and
    [int]$dotnetVersion.Split('.')[0] -ge 10 -and
    $templateOutput -match '(?i)winui'
if ([string]::IsNullOrWhiteSpace($vsPath) -and -not $cliToolchainReady) {
    Add-Failure "Visual Studio with the WinUI application development workload or the complete .NET CLI WinUI toolchain is required."
} elseif ([string]::IsNullOrWhiteSpace($vsPath)) {
    Add-Warning "Visual Studio was not found; the verified .NET CLI WinUI toolchain will be used."
}

if ($null -eq (Get-CommandPath "git")) {
    Add-Failure "Git is missing. Install Git for Windows."
}
if ($null -eq (Get-CommandPath "gh")) {
    Add-Warning "GitHub CLI is not installed; local builds still work, but GitHub handoff commands will not."
}

if ($Install -and $requiredFailures.Count -gt 0) {
    $winget = Get-CommandPath "winget"
    if ($null -eq $winget) {
        throw "WinGet is required for automatic setup. Install App Installer or run the documented manual setup."
    }

    Write-Host "Installing the Microsoft WinUI development configuration..."
    & winget configure -f https://aka.ms/winui-config --accept-configuration-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) {
        throw "WinGet configuration failed with exit code $LASTEXITCODE."
    }

    Write-Host "Setup completed. Re-run this script without -Install to verify the refreshed environment."
    exit 0
}

Write-Host "zWorkforce Windows client environment"
Write-Host "  OS:       $osLabel"
Write-Host "  .NET:     $(if ($dotnetVersion) { $dotnetVersion } else { 'missing' })"
Write-Host "  Visual Studio: $(if ($vsPath) { $vsPath.Trim() } else { 'missing' })"
Write-Host "  SDKs:     $(if ($sdkVersions.Count) { $sdkVersions -join ', ' } else { 'missing' })"
Write-Host "  Dev Mode: $(if ($devMode -eq 1) { 'enabled' } else { 'disabled' })"
Write-Host "  WinUI template: $(if ($templateOutput -match '(?i)winui') { 'present' } else { 'missing' })"

if ($warnings.Count -gt 0) {
    Write-Host "Warnings:"
    $warnings | ForEach-Object { Write-Warning $_ }
}
if ($requiredFailures.Count -gt 0) {
    Write-Host "Missing requirements:"
    $requiredFailures | ForEach-Object { Write-Error $_ }
    exit 2
}

Write-Host "All required WinUI client build prerequisites are present."
