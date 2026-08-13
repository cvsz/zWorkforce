# ECC for Codex CLI

This supplements the root `AGENTS.md` with a repo-local ECC baseline.

## Repo Skill

- Repo-generated Codex skill: `.agents/skills/zWorkforce/SKILL.md`
- ProMeta support skills: `.agents/skills/zworkforce-*/SKILL.md`
- Claude-facing companion skill: `.claude/skills/zWorkforce/SKILL.md`
- Keep user-specific credentials and private MCPs in `~/.codex/config.toml`, not in this repo.

## MCP Baseline

Treat `.codex/config.toml` as the default ECC-safe baseline for work in this repository.
The generated baseline enables GitHub, Context7, Exa, Memory, Playwright, and Sequential Thinking.

## Multi-Agent Support

- Explorer: read-only evidence gathering
- Reviewer: correctness, security, and regression review
- Docs researcher: API and release-note verification
- ProMeta agents: use `examples/prometa-agent-catalog.json` with
  `examples/prometa-skills.json` as the runtime seed reference.

## Workflow Files

No dedicated workflow command files were generated for this repository. Use
the repository `Makefile`, package scripts, and GitHub Actions workflows as the
authoritative task scaffolds.
