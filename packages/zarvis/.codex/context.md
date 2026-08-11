# Codex Zeaz Platform Context

## Language and Coding Standards
- **Communication**: Always talk in Thai when interacting with users.
- **Code & Technical Assets**: All code, comments, documentation, and technical definitions must be in English.

## Mission
Operate as an enterprise Cloudflare platform engineer for `ZeazDev` on `zeaz.dev` with deterministic, GitOps-safe workflows.

## Execution Guardrails
- Enforce least-privilege Cloudflare API token usage per workload (DNS, Zero Trust, Workers, WAF, Tunnel, R2).
- Require runtime validation for all required environment variables before any mutate operation.
- Run drift detection before apply operations and after incident recovery.
- Never hardcode credentials, account IDs, zone IDs, or private keys.

## Required Validation Contract
Use `zeaz-platform/scripts/contracts/environment-contract.json` and `zeaz-platform/scripts/validate.sh` before install, plan, apply, rotate, backup, and restore.

## Standard Operator Flow
1. `make -C zeaz-platform validate`
2. `make -C zeaz-platform plan-tier`
3. `make -C zeaz-platform mcp-config`
4. `make -C zeaz-platform plan`
5. `make -C zeaz-platform apply`
6. `make -C zeaz-platform drift`

## Incident and Recovery
- Use `zeaz-platform/scripts/backup.sh` before major changes.
- Use `zeaz-platform/scripts/restore.sh` for deterministic rollback.
- Audit token scope drift with `zeaz-platform/scripts/validate-token-scopes.sh`.


## MCP Runtime
- Regenerate local MCP config with `make -C zeaz-platform mcp-config` after token rotation.

## Local Model Runtime
- Ollama local model registry: `configs/platform/local-models.json`.
- Default local model: `gpt-oss:20b-8k`.
- Local-only endpoint: `http://localhost:11434`.
- Validate with `node scripts/platform/validate-local-ollama-models.mjs`.
