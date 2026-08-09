# zWorkforce Windows 11 Client Design

**Date:** 2026-08-09  
**Status:** Approved for implementation  
**Product:** `ZWorkforceClient`

## Intent

Provide a native Windows 11 desktop client for operators who connect to an
existing zWorkforce control plane. The client is an operator console, not a
second server runtime: authentication, tenant authorization, policy,
approvals, task execution, model/provider credentials, and durable state stay
on the server.

The client must work against a local server such as
`http://localhost:9569` and against a deployed HTTPS control plane without
requiring server-side changes.

## Verified server contract

The current server exposes:

- unauthenticated `GET /health` and `GET /ready`;
- authenticated `/api/v1/*` routes using a bearer API key or the server's
  configured identity boundary;
- tenant selection through `X-Tenant-ID` for credentials allowed to select a
  tenant;
- `Idempotency-Key` for retry-safe task and workflow writes;
- JSON errors shaped as
  `{"error":{"code":"...","message":"..."},"request_id":"..."}`.

The authoritative route implementation is `zworkforce/api.py` and the public
route inventory is `docs/API.md`. The client will not infer permissions from
the UI. A failed request remains authoritative, and the client will display
the server's error code/message and request ID when available.

## Scope

### Connection and security

- configurable base URL with normalization to a single trailing slash;
- API key and optional tenant ID inputs;
- health/readiness test before authenticated loading;
- bearer authentication and `X-Tenant-ID` on authenticated requests;
- API key stored with Windows `PasswordVault`, never in source, logs, crash
  messages, or ordinary settings files;
- base URL and non-secret preferences stored in application settings;
- explicit disconnect and credential removal;
- HTTPS warning for non-local HTTP endpoints;
- request timeout, cancellation, and safe error mapping;
- no automatic retry of mutating operations unless the request has an
  idempotency key.

### Operator shell

The app is a packaged C# WinUI 3 desktop application using the standard
`NavigationView` shell, one main window, theme resources, keyboard navigation,
high-contrast-safe colors, and light/dark mode. Initial destinations are:

- **Overview:** metrics, provider availability, queue/dead-letter signals,
  recommendations, and recent activity;
- **Tasks:** paginated task list, search/status filters, task details, events,
  approvals, and server-authorized actions;
- **Agents:** agent and version inventory;
- **Automation:** workflows, workflow runs, schedules, event rules, and
  operator tick actions;
- **Knowledge:** memories, RAG search, skills, and artifacts;
- **Governance:** policies, budgets, SLO/economics, audit, tenants, and API
  keys, shown or enabled only when the server permits the operation;
- **Settings:** connection, theme, diagnostics, and credential removal.

The complete API surface is represented in the client service layer even when
some advanced pages start as table/detail views. This avoids creating a UI
that silently omits supported server capabilities while keeping the first
release maintainable.

### API coverage

The client service layer will cover these route groups:

```text
/health, /ready
/api/v1/overview, providers, models, recommendations, tools
/api/v1/agents, agent-templates, policies
/api/v1/tasks and task detail/events/approvals/actions
/api/v1/workflows, workflow-runs, workflow-tick, schedules, event-rules,
  events, scheduler-tick
/api/v1/evaluation-suites, evaluation-runs, evaluation-tick
/api/v1/memories, rag, rag/reindex, artifacts, skills
/api/v1/budgets, chargeback, capacity, slo, slo/status, economics
/api/v1/tenants, api-keys, audit, audit/verify, tool-events
```

The MCP endpoint is intentionally not duplicated in the first native UI. It
remains available to MCP clients and can be added later as an explicitly
documented integration rather than an opaque second protocol implementation.

## Architecture

```text
WinUI 3 shell/pages
        |
ViewModels + commands
        |
ZWorkforceClient.Core
  ApiClient | models | error mapping | request policies
        |
HttpClient + Windows credential/settings adapters
        |
zWorkforce REST API
```

Repository layout:

```text
ZWorkforceClient/
  ZWorkforceClient.sln
  src/
    ZWorkforceClient.Core/       # net10.0, platform-neutral API/domain code
    ZWorkforceClient/            # packaged WinUI 3 app
  tests/
    ZWorkforceClient.Core.Tests/ # contract and service tests
  build/
    windows/                     # setup, build, package, and verify scripts
  docs/
    WINDOWS-CLIENT.md
```

The core library uses `System.Net.Http.Json` and `System.Text.Json` with
explicit DTOs for stable server payloads and `JsonElement` extension payloads
where the server intentionally returns domain-specific JSON. It exposes
async cancellation-aware methods, a common response/error pipeline, and
idempotency-key generation for writes.

The WinUI project depends on the core library and owns only presentation,
navigation, Windows credential storage, app settings, and window lifecycle.
No API key is placed in a view model that is persisted or serialized.

## Packaging and environment

The client uses the default packaged WinUI 3 path because the product needs a
normal Windows installation/update path and package identity for Windows
credential/settings integration. The supported build host is Windows 11 with:

- Windows 11 22H2 or later;
- Visual Studio 2022/2026 with the WinUI application development workload;
- a supported .NET SDK (the project targets .NET 8 for the current Windows App
  SDK baseline);
- Windows SDK 10.0.26100.0 or later;
- Windows App SDK/WinUI 3 tooling installed by the workload;
- Developer Mode enabled for local deployment/debugging;
- Git and optionally GitHub CLI for repository/release operations.

`build/windows/Install-Prerequisites.ps1` is the documented idempotent setup
entry point. It checks the OS, .NET SDK, Visual Studio workload, Windows SDK,
WinUI template, and Developer Mode. It does not write server credentials.
`build/windows/Build-Client.ps1`, `Test-Client.ps1`, and
`Package-Client.ps1` make the local workflow repeatable.

The project targets the current .NET 10 SDK and stable Windows App SDK 2.3.1.
The current Linux agent cannot compile or launch WinUI. GitHub Actions on
`windows-latest` is therefore the authoritative Windows build/launch check;
the local agent will still validate source structure, YAML, scripts, and the
Python server test suite.

## Testing strategy

Tests are written before implementation for the platform-neutral core:

- URL normalization and request header construction;
- authentication and tenant header behavior;
- JSON error/request-ID extraction;
- idempotency-key behavior on writes;
- health/readiness response parsing;
- task action and list/detail route construction;
- cancellation and timeout mapping;
- credential/settings adapters through interfaces, with Windows adapters
  covered by build-time and Windows CI smoke checks.

The Windows workflow builds the packaged app, runs core tests, performs a
launch smoke check, and uploads the MSIX and symbol/log artifacts on release.
The client must not require a live zWorkforce server for unit tests.

## GitHub delivery

Add a dedicated `windows-client.yml` workflow that:

1. runs on pull requests and pushes touching the client, setup scripts, docs,
   or the workflow;
2. uses a Windows runner;
3. verifies the environment and WinUI template;
4. restores, builds, tests, packages, and launches the client for a bounded
   smoke check;
5. uploads build diagnostics on failure;
6. publishes an MSIX artifact on version tags through the existing release
   process without exposing credentials.

Repository documentation will explain branch protection requirements: the
Windows client check must be required alongside the existing Python, security,
CodeQL, and dependency checks before merge.

## Non-goals

- moving model/provider secrets to the client;
- embedding a Python runtime or worker in the Windows app;
- bypassing server RBAC, scopes, tenant checks, policy, or approvals;
- inventing a second authentication protocol;
- claiming local build success when no Windows toolchain is present;
- making MCP a second UI/API implementation in this release.

## Acceptance criteria

1. A clean Windows 11 host can run the documented prerequisite check and
   scaffold/build/package the project.
2. The app launches to a real top-level window and displays a connection page.
3. Against `http://localhost:9569`, a user can connect with an API key and
   tenant, see readiness, load overview/tasks/agents/providers/memories, and
   perform permitted task actions.
4. All supported route groups have service-layer methods and tests for route,
   headers, errors, and idempotency behavior.
5. Secrets are stored only through the Windows credential adapter and are not
   present in logs or ordinary settings.
6. The app supports light/dark/high-contrast-safe visuals and keyboard access
   for the primary workflow.
7. GitHub Actions builds/tests the client on Windows and exposes diagnostics
   and release artifacts.
8. Existing server tests and release checks remain green.
