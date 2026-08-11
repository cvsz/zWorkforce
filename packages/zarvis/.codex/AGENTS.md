# ECC for Codex CLI

## Language and Coding Standards
- **Communication**: Always talk in Thai when interacting with users.
- **Code & Technical Assets**: All code, comments, documentation, and technical definitions must be in English.

This supplements the root `AGENTS.md` with a repo-local ECC baseline.

## Repo Skill

- Repo-generated Codex skill: `.agents/skills/zeaz-platform/SKILL.md`
- Claude-facing companion skill: `.claude/skills/zeaz-platform/SKILL.md`
- Keep user-specific credentials and private MCPs in `~/.codex/config.toml`, not in this repo.

## MCP Baseline

Treat `.codex/config.toml` as the default ECC-safe baseline for work in this repository.
The generated baseline enables GitHub, Context7, Exa, Memory, Playwright, and Sequential Thinking.
MCP entries include explicit startup timeouts and quiet `npx` invocation so first-run package installs and remote handshakes do not fail noisily.
Use `scripts/sync-ecc-to-codex.sh` to merge the full ECC-managed MCP set, including optional Supabase, into `~/.codex/config.toml` without committing user-specific project refs or credentials.
Use `scripts/sync-codex-agents-skills.sh --apply` when the user asks to install all repo ECC agents and skills into the user-level Codex surfaces.

## Multi-Agent Support

- Explorer: read-only evidence gathering
- Reviewer: correctness, security, and regression review
- Docs researcher: API and release-note verification
- Phase planner: phase-scoped Cloudflare platform delivery planning
- Security guardian: secrets, access policy, and guarded automation review
- Validation operator: offline validation mapping without infrastructure mutation

## Workflow Files

- No dedicated workflow command files were generated for this repo.

Use these workflow files as reusable task scaffolds when the detected repository workflows recur.

## Master Meta Cloud Suite

- Suite manifest: `.codex/suite/master-meta-cloud-suite.json`
- Operator guide: `docs/codex/master-meta-cloud-suite.md`
- Phase prompt templates: `docs/codex/prompts/`
- Offline validation: `python3 docs/codex/scripts/validate_codex_suite.py` or `make codex-suite-validate`

Use the suite when a request is broad, meta-level, or asks for Codex Cloud orchestration. Keep work phase-scoped and never convert generated plans into live infrastructure mutation.
