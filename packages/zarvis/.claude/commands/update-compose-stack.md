---
name: update-compose-stack
description: Workflow command scaffold for update-compose-stack in z-platform.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /update-compose-stack

Use this workflow when working on **update-compose-stack** in `z-platform`.

## Goal

Adds or modifies Docker Compose stack configurations for local or staging environments.

## Common Files

- `compose.yml`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Add or modify compose.yml to reflect service or network changes

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.