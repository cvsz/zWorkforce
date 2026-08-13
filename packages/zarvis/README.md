# Z.A.R.V.I.S. Package Suite

This directory is the consolidated Z.A.R.V.I.S. product and platform suite shipped inside `cvsz/zWorkforce` as `packages/zarvis`.

It keeps only the Z.A.R.V.I.S. applications, deployable services, shared contracts, and operational documentation needed to build and operate the assistant suite inside `zWorkforce`.

## Initial domains

- Assistant surfaces: browser console, Windows operator client, and realtime voice
- Orchestration: command validation, task approval, action gateway, audit events
- Context: memory, perception, proactive signals, and retention controls
- Operations: release, backup, observability, and owner-domain runbooks

## Package layout

```text
apps/       Z.A.R.V.I.S. user-facing applications
services/   Z.A.R.V.I.S. APIs, gateways, and workers
packages/   Shared libraries and API contracts
docs/       Architecture, runbooks, requirements, and release records
tools/      Developer and operator tooling
```

## Validation

```bash
pnpm install --frozen-lockfile
pnpm peers check
pnpm test
```

The ZARVIS API additionally runs its Python test suite and dependency audit.
ZARVIS Windows projects are restored on Ubuntu, then built and tested on the
Windows runner. The Windows workflow separately packages and smoke-tests the
ZWorkforceClient application. Root GitHub Actions are the authoritative gates.

## Boundary policy

This package intentionally excludes non-Z.A.R.V.I.S. products and legacy platform services. New additions must have an owner, dependency inventory, tests, security review, and rollback path.

Provider and model allowlists are tracked explicitly. Secrets, payment credentials, wallet keys, and provider API keys stay outside the repository.

- [Architecture](docs/architecture/README.md)
- [Release runbook](docs/operations/zarvis-local-release-runbook.md)

## Local realtime voice

The optional voice stack adds a browser voice surface, short-lived WebSocket ticket gateway, and a local Hugging Face speech pipeline while keeping LLM access in server-side Z.A.R.V.I.S. services.

```text
Browser -> apps/zvoice -> services/voice-gateway -> services/voice-agent
                                                     -> Ollama / llama.cpp / vLLM
```

- [Voice architecture](docs/architecture/voice-agent.md)
- [Voice operations runbook](docs/operations/voice-agent.md)
- [Voice Compose overlay](compose.voice.yml)

## Security

No secrets, payment credentials, wallet keys, MPC shares, Cloudflare tokens, or provider API keys may be committed. See [SECURITY.md](SECURITY.md).
