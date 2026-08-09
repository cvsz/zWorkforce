# Windows 11 Client Implementation Plan

> **Execution note:** follow this plan in order. Keep the existing server
> hardening changes in the worktree; do not reset or checkout them away.

## Goal

Deliver a packaged C# WinUI 3 Windows 11 client that connects to the existing
zWorkforce REST API, provides complete route-group service coverage and core
operator pages, documents the Windows environment, and is built/tested by
GitHub Actions on a Windows runner.

## Constraints

- Preserve all pre-existing server changes in the dirty worktree.
- Use the standard WinUI 3 packaged project shape and native WinUI controls.
- Keep API-key material out of ordinary settings, logs, tests, and telemetry.
- Test platform-neutral code before implementation code.
- Do not claim local WinUI build/launch success on this Linux host; obtain that
  evidence from the Windows CI runner or a Windows host.

## Work items

### 1. Test-first core contract

Files:

- `ZWorkforceClient/tests/ZWorkforceClient.Core.Tests/ZWorkforceClient.Core.Tests.csproj`
- `ZWorkforceClient/tests/ZWorkforceClient.Core.Tests/ApiClientTests.cs`
- `ZWorkforceClient/tests/ZWorkforceClient.Core.Tests/ConnectionSettingsTests.cs`

Write failing tests for URL normalization, bearer and tenant headers, JSON
error/request-ID mapping, health/readiness parsing, idempotency keys, route
construction, task actions, and cancellation. Use a fake `HttpMessageHandler`
so no live server or secret is required.

### 2. Core project and API client

Files:

- `ZWorkforceClient/src/ZWorkforceClient.Core/ZWorkforceClient.Core.csproj`
- `ZWorkforceClient/src/ZWorkforceClient.Core/Api/ApiClient.cs`
- `ZWorkforceClient/src/ZWorkforceClient.Core/Api/ApiException.cs`
- `ZWorkforceClient/src/ZWorkforceClient.Core/Api/ApiRequest.cs`
- `ZWorkforceClient/src/ZWorkforceClient.Core/Models/ApiModels.cs`
- `ZWorkforceClient/src/ZWorkforceClient.Core/Models/JsonModels.cs`
- `ZWorkforceClient/src/ZWorkforceClient.Core/Services/ConnectionSettings.cs`

Implement an immutable connection configuration, a single authenticated HTTP
pipeline, typed stable responses, and explicit methods for every documented
route group. Keep flexible domain payloads as `JsonElement` rather than
silently dropping fields. Writes generate a UUID idempotency key by default;
callers may supply a stable key when retrying a known operation.

### 3. Windows shell and security adapters

Files:

- `ZWorkforceClient/src/ZWorkforceClient/ZWorkforceClient.csproj`
- `ZWorkforceClient/src/ZWorkforceClient/App.xaml`
- `ZWorkforceClient/src/ZWorkforceClient/App.xaml.cs`
- `ZWorkforceClient/src/ZWorkforceClient/MainWindow.xaml`
- `ZWorkforceClient/src/ZWorkforceClient/MainWindow.xaml.cs`
- `ZWorkforceClient/src/ZWorkforceClient/Services/WindowsCredentialStore.cs`
- `ZWorkforceClient/src/ZWorkforceClient/Services/WindowsSettingsStore.cs`
- `ZWorkforceClient/src/ZWorkforceClient/Styles/ThemeResources.xaml`

Use a packaged WinUI project targeting `net10.0-windows10.0.26100.0`, the
stable Windows App SDK 2.3.1 package selected in central package management,
and x64/ARM64 package profiles. Keep startup minimal: load non-secret
settings, create the shell, and let pages connect asynchronously.

### 4. Core operator pages

Files:

- `Pages/ConnectionPage.*`
- `Pages/OverviewPage.*`
- `Pages/TasksPage.*`
- `Pages/AgentsPage.*`
- `Pages/AutomationPage.*`
- `Pages/KnowledgePage.*`
- `Pages/GovernancePage.*`
- `Pages/SettingsPage.*`
- `ViewModels/*.cs`

Build the shell with `NavigationView`, `InfoBar`, `CommandBar`, `ListView`,
`DataGrid` only if the standard controls are insufficient, and `ContentDialog`
for destructive/approval decisions. Make narrow-window behavior explicit,
use theme resources, and expose accessible names/tooltips for icon actions.

### 5. Environment and local build workflow

Files:

- `build/windows/Install-Prerequisites.ps1`
- `build/windows/Build-Client.ps1`
- `build/windows/Test-Client.ps1`
- `build/windows/Package-Client.ps1`
- `docs/WINDOWS-CLIENT.md`
- `ZWorkforceClient/global.json`
- `ZWorkforceClient/Directory.Packages.props`

Provide idempotent checks for Windows version, .NET SDK, Visual Studio WinUI
workload, Windows SDK, WinUI template, Developer Mode, and Git/GitHub CLI.
The scripts must fail with actionable output and must not print credential
values. Document packaged deployment, local server connection, signing, and
the difference between framework-dependent and self-contained MSIX.

### 6. GitHub automation

Files:

- `.github/workflows/windows-client.yml`
- `.github/workflows/release.yml` (extend existing release artifacts)
- `.github/dependabot.yml` (add NuGet ecosystem if appropriate)
- `.github/ISSUE_TEMPLATE/windows-client-bug.yml`

The Windows workflow restores, builds, tests, packages, and runs a bounded
launch smoke check. Upload `bin`/`obj` diagnostics on failure. Release tags
publish the MSIX and checksums without embedding credentials. Keep permissions
least-privilege and document the required branch-protection check.

### 7. Verification and handoff

Run:

- `git diff --check`;
- local source/YAML/PowerShell/XML validation;
- the existing `make check` and production regression suite;
- Windows GitHub workflow on the feature branch;
- GitHub workflow logs and artifacts inspection;
- a final status audit ensuring no server fix was lost.

Only claim the Windows client is build-ready after the Windows runner produces
a package and confirms a real top-level process/window or an equivalent
launch smoke signal. If the runner cannot display a desktop window, retain a
separate build/package result and state the launch limitation explicitly.
