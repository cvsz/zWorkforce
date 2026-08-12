# Z.A.R.V.I.S. Package Suite

This directory is the consolidated Z.A.R.V.I.S. product and platform suite shipped inside `cvsz/zWorkforce` as `packages/zarvis`.

It separates user applications, deployable services, shared packages, infrastructure, and operational documentation. The legacy repository remains unchanged and is the migration source of record.

## Initial domains

- AI workspace: chat, coding, agent orchestration, research jobs
- Platform core: identity, tenant boundaries, usage and audit events
- Financial boundary: billing and ledger integration only
- Operations: Cloudflare Zero Trust, GitOps, observability

## Package layout

```text
apps/       User-facing applications
services/   Deployable APIs and workers
packages/   Shared libraries and API contracts
workers/    Cloudflare Workers
infrastructure/ Infrastructure definitions and deployment manifests
configs/    Non-secret schemas and examples
docs/       Architecture, ADRs, runbooks and migration records
tools/      Developer tooling and generators
```

## Validation

```bash
pnpm install --frozen-lockfile
pnpm peers check
pnpm test
```

The ZARVIS API additionally runs its Python test suite and dependency audit;
Windows projects are restored on Ubuntu and built, tested, packaged, and smoke
tested on the Windows runner. Root GitHub Actions are the authoritative gates.

## Migration policy

This repository does not bulk-copy legacy applications. Each migration must have an owner, dependency inventory, tests, security review, and rollback path.

Provider and model allowlists are tracked explicitly. Secrets, payment credentials, wallet keys, and provider API keys stay outside the repository.

- [Provider list](PROVIDER-LIST.md)
- [Migration manifest](docs/migration/manifest.md)
- [Full execution plan](docs/migration/execution-plan.md)

## Local realtime voice

The optional voice stack adds a browser voice surface, short-lived WebSocket ticket gateway, and a local Hugging Face speech pipeline while preserving the AI Gateway as the single LLM policy boundary.

```text
Browser -> apps/zvoice -> services/voice-gateway -> services/voice-agent
                                                  -> services/ai-gateway
                                                     -> Ollama / llama.cpp / vLLM
```

- [Voice architecture](docs/architecture/voice-agent.md)
- [Voice operations runbook](docs/operations/voice-agent.md)
- [Voice Compose overlay](compose.voice.yml)

## Security

No secrets, payment credentials, wallet keys, MPC shares, Cloudflare tokens, or provider API keys may be committed. See [SECURITY.md](SECURITY.md).
