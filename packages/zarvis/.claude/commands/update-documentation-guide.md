---
name: update-documentation-guide
description: Workflow command scaffold for update-documentation-guide in z-platform.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /update-documentation-guide

Use this workflow when working on **update-documentation-guide** in `z-platform`.

## Goal

Creates or updates documentation guides and ensures they are linked in the documentation index.

## Common Files

- `docs/operations/local-compose.md`
- `docs/operations/README.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create or update a documentation guide file in docs/operations/
- Update docs/operations/README.md to link the new or updated guide
- Optionally, finalize or refresh the guide with further edits

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.