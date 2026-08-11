---
name: update-environment-configuration
description: Workflow command scaffold for update-environment-configuration in z-platform.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /update-environment-configuration

Use this workflow when working on **update-environment-configuration** in `z-platform`.

## Goal

Adds or corrects environment configuration templates for local or staging environments.

## Common Files

- `.env.example`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Add or update .env.example with new variables or corrections
- Document changes or guidance in commit messages

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.