# Gemini Instructions

This file mirrors the repository guidance for Gemini-style coding assistants.

## Repository goal

`z-platform` is a security-first successor platform extracted incrementally from `cvsz/zeaz-platform`. Preserve safe product behavior while replacing direct provider access, unsafe financial surfaces, migration-only adapters, and unapproved execution paths with explicit platform boundaries.

## Required behavior

- Read `AGENTS.md` before making changes.
- Follow `docs/requirements/master-requirements.md` for requirement IDs and acceptance criteria.
- Follow `docs/operations/production-master.md` for production-affecting work.
- Keep AI provider credentials server-side behind the AI Gateway.
- Keep browser clients free of secrets and service tokens.
- Require approval for mutating agent tools, workspace shell, workspace deploy, infrastructure, and production traffic.
- Preserve ZWallet as a billing-ledger adapter only.

## Do not do

- Do not commit secrets or production identifiers.
- Do not expose provider keys to browser code.
- Do not add wallet signing, card handling, KYC, MPC, or swap capability to AI or billing paths.
- Do not bypass approval gates.
- Do not bulk-copy legacy code without tests, inventory, security review, and rollback notes.
- Do not install files, configs, or binaries outside the `z-platform` directory. The installation must remain standalone.

## Output expectations

Prefer focused changes, clear commit messages, updated tests, and updated docs when behavior changes.
