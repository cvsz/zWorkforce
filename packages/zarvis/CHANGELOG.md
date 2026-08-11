# Changelog

All notable changes to `z-platform` should be documented in this file.

This project follows a human-readable changelog style. Dates use `YYYY-MM-DD`.

## Unreleased

### Added

- Z.A.R.V.I.S. first vertical slice with a voice/text command console, constrained read-only GitHub repository status orchestration, speech-ready responses, versioned contracts, structured audit events, security threat model, operations runbook, and 12 focused tests.
- Staging decision record validation now enforces the approved identity-provider and tenant-claim mapping snapshot in `scripts/staging-decision-record.json`, with a workflow check and repo-local tests guarding the contract.
- Staging decision record schema coverage now records the approved operator decision contract in `schemas/operations/staging-decision-record.schema.json`, with repo-local tests checking the schema shape alongside the validator.
- Phase 6 operator-input register now records the remaining Issue #1 `PENDING_OPERATOR` stack in `scripts/phase-6-operator-inputs.json`, with schema and validator coverage that keep the register explicit without inventing values.
- Production release record template and schema now carry an explicit operator context (`stagingReviewer`, `incidentOwner`, `escalationRoute`, `watchWindow`) that matches the external readiness harness, with repo-local tests covering the contract.
- GitHub environment helper and readiness docs now surface the operator-owned review fields (`STAGING_REVIEWER`, `INCIDENT_OWNER`, `ESCALATION_ROUTE`, `WATCH_WINDOW`, and production reviewer selectors) from the dotenv overlays, with repo-local drift tests tied to the current `origin/main` SHA.
- Release governance now includes an explicit issue-item mapping for the remaining `PENDING_OPERATOR` values so the final-release workflow can point each operator decision at the correct record or workflow without fabricating approvals.
- Release governance now has repo-level coverage for the operator-signoff path: the phase-6 operator input register, operational ownership record, and production release record are linked by focused validation tests and workflow-shape checks.
- Phase 6 API now exposes a read-only Supabase Data API bridge at `/supabase/read`, with server-side anon-key handling, base-URL and table validation, and route-level success/failure tests.
- GitHub environment bootstrap helper now imports populated keys from `.env`, `.env.phase6`, and `.env.phase6.server` into GitHub environment variables and secrets while keeping reviewer selectors explicit.
- GitHub Actions workflow pins upgraded to Node 24-compatible releases across checkout, setup-node, setup-python, setup-go, and artifact upload steps, with repository tests updated to match the new workflow contracts.
- Deployment readiness workflows now verify that the requested release SHA exists in `cvsz/z-platform` before checkout, so stale or invalid SHAs fail closed instead of surfacing as broken deployment records.
- CI, validate, and CodeQL workflows now provision Node 24 before installing `pnpm@11.4.0`, which keeps the repository toolchain compatible with the pinned package manager and prevents `node:sqlite` install failures on Node 20 runners.
- CodeQL Advanced workflow now targets the available self-hosted Linux/X64 runner labels instead of a missing custom label, so the job can start on the current runner pool while keeping security-analysis execution on self-hosted infrastructure.
- Release template and zctl apiVersion identifiers now use `zeaz.dev` instead of `z-platform.io`.
- GitHub issue templates, sponsor metadata, and Discussions entry points were added for repository community setup.
- Phase 6 API now exposes a verified GitHub webhook endpoint at `/webhooks/github` on the Cloudflare-backed Phase 6 hostname, with signature validation and failure-path tests.
- Cloudflare Terraform examples and installer defaults now use service-named public hostnames such as `phase6.zeaz.dev`, `zchat.zeaz.dev`, and `zai.zeaz.dev`.
- Shared readiness probe helpers now set `Content-Type: application/json` whenever a JSON body is present, so POST-based external checks are sent with the expected content type.
- External readiness manifest validation now rejects placeholder HTTPS probe URLs such as `staging.example.invalid` and localhost-style endpoints.
- External readiness validation now rejects explicitly invalid probe `expectedStatus` values instead of ignoring falsy inputs.
- CodeQL Advanced workflow hardening that provisions Node, pnpm, Go, and Python toolchains before analysis on the available self-hosted Linux/X64 lane, with repo-local ordering tests for the setup steps.
- CodeQL Advanced workflow update that runs on the available self-hosted Linux/X64 lane and loads the broader `security-and-quality` query suite, with repo-local workflow-shape tests; alert-closure evidence still requires a PR-head runner execution.
- CI and validate Node workspace jobs now install dependencies before testing so the AI Gateway disconnect contract can resolve its app imports in GitHub Actions.
- ZChat browser-local dark mode preference with system fallback.
- ZChat manual conversation title editing that updates the active chat and history sidebar.
- ZChat active conversation export controls for markdown copy and JSON download.
- ZChat browser-local prompt template library with built-in presets, custom template saving, and "start from template" chat creation.
- ZChat per-conversation system prompt editing with browser persistence and gateway forwarding.
- AI Gateway disconnect-aware upstream cancellation with a real-socket regression test for client disconnects.
- AI Gateway container startup contract tests covering the start command, health route, fail-closed authentication, and authorization-log redaction.
- Root `Makefile` GPG helpers for signed commit, push, pull, and finalize workflows using the same `COMMIT_MSG` interface as the older `zeaz-platform` repo.
- Current-head evidence record for `923c3a190fbf626faae076bf5faa43a4d03a9703`, preserving its failed deployed-smoke classification and immutable SBOM metadata.
- Current-head evidence synchronization for `2db36e428fa95457e0559dabc224b7d8ff10d289`, including its passing SHA-bound deployed-smoke and SBOM artifacts while keeping unresolved security alerts blocked.
- Immutable release-evidence validation that binds recorded, approved, and observed revisions to the exact release-candidate commit.
- Migration feature matrix, execution records, and validation report for the release-evidence slice.
- Project overview documentation under `docs/project`.
- Master requirements documentation under `docs/requirements`.
- Production master document and operations index under `docs/operations`.
- Platform operations workflow for dependency checks, SBOM generation, and provenance verification.
- CI coverage for migrated Node and Python runtimes.
- AI Gateway, ZAI Coder, ZChat, agent orchestration, workspace runtime, billing ledger, and ZWallet migration boundaries.
- **Agent Control Panel:** Full-stack UI for managing multi-provider API keys and automatic rotation logic.
- **AI Gateway Redis Pool:** Multi-provider rotation pool, failure injection limits, and fallback strategies.
- **AI Gateway Streaming & Uploads:** Native server-sent events (SSE) streaming support and binary payload pass-through.
- **ZChat Generation Stop:** Stop control now aborts active browser and upstream chat generation while preserving partial assistant output.
- **Cloudflare Edge Worker:** Initial proxy script and `wrangler.toml` for authentication and routing at the edge.
- **Browser Credential Isolation:** Automated verification scripts ensure `sk-` keys and `Z_PLATFORM_SERVICE_TOKEN` are completely blocked from frontend bundles.
- **Human Client QA & Identity Provider:** Automated static checks for screen-reader/accessibility support, responsive layouts, and Cloudflare Access external identity integration in ZChat.
- **Observability Stack:** Added automated verification script `verify-observability-stack.mjs` to validate Prometheus metrics collection, Grafana health, and Jaeger distributed trace propagation.
- **Evidence drift sync and SHA-binding gate:** Restored `validate-release-evidence.yml` CI workflow removed in PR #44; cleared stale `releaseSha` from `staging-readiness-manifest.json`; added rollback candidates for PRs #43 and #44; recorded the then-current `main` head (`624183524fd3edc9666ddce7c64acafa1130fa7e`). The current-head record now supersedes that drift notice.
- **Compose Service Discovery Fix:** Fixed `redis` network configurations in `compose.yml` to use `z-platform-internal` network, enabling proper DNS resolution and database connection for the `ai-gateway` service.

### Fixed

- Removed tracked Cloudflare Terraform state, backup state, and committed `terraform.tfvars` from version control, and added a stack-local ignore file so future state files stay out of the repo.
- Root `pnpm test` now runs workspace tests serially, which avoids the recursive workspace concurrency flake that surfaced in the default parallel runner.
- `agent-control-panel` now uses a dedicated Next.js Dockerfile that installs dependencies, builds the app, and prunes dev dependencies before `npm start`, which stops the compose restart loop caused by the missing `next` binary.
- Deployed smoke now accepts the committed ZChat semantic main region and current responsive breakpoint (`<main class="shell">` and `@media (max-width: 720px)`), with a regression test guarding the static markup used by the smoke script.

### Security

- Resolve CodeQL findings for workspace path containment, AI Gateway rate limiting, default-deny CORS, and Cloudflare installer authorization-header logging; override transitive PostCSS to patched version `8.5.19`.
- Kept production and external traffic disabled while making Gateway runtime dependency installation explicit and scoped to that image.
- Release evidence copied from another commit is rejected before approval or deployment recording.
- Documented gateway-only provider access and browser secret isolation.
- Documented explicit approval gates for agent tools, workspace shell, workspace deploy, infrastructure, and production traffic.
- Documented denial of wallet signing, cards, KYC, MPC, and swaps from AI and billing paths.

## 0.1.0 - 2026-07-13

### Added

- Initial security-first platform foundation extracted incrementally from `cvsz/zeaz-platform`.
- Baseline migration manifest, execution plan, architecture docs, CI, and operations runbooks.
