---
name: zworkforce-zeto-content-factory
description: Operate the Zeto AI Content Factory including ProMeta prompt compilers, multi-platform publishing adapters, QA scorecards, and the M12 tool registry.
---

# zWorkforce Zeto Content Factory

Produce and publish content through the Zeto pipeline without skipping
quality gates.

## Workflow

1. Identify the content type, target platform(s), and the ProMeta prompt
   template it should compile through.
2. Compile the prompt and generate a draft, keeping platform-specific
   constraints (length, format, media type) explicit rather than assumed.
3. Run the QA scorecard against the draft before it is treated as
   publishable; do not publish content that fails the configured QA
   threshold.
4. Route publishing through the correct multi-platform adapter for the
   target destination, and verify the adapter's response confirms
   acceptance rather than assuming success.
5. Record the compiled prompt, QA score, and publish confirmation as
   provenance for the generated artifact.

## References

- `packages/zeto`
- `zworkforce/tools.py` (`media_generate`)
- `README.md` Zeto section

## Output

Report content type, platform target, QA scorecard result, publish
confirmation or rejection reason, and artifact provenance.
