---
name: zworkforce-evaluation-suites
description: Design and run zWorkforce A/B model evaluation suites that compare Luna/Terra/Sol tier variants on real tasks and recommend the quality/cost winner.
---

# zWorkforce Model Evaluation Suites

Compare model/agent strategies on evidence, not intuition.

## Workflow

1. Define the task set the evaluation suite will run: representative,
   reproducible, and scored with a deterministic or well-specified rubric.
2. Configure the tier variants being compared (Luna/Terra/Sol, or specific
   provider/model combinations) and hold everything else constant.
3. Run the suite and capture quality score, cost, and latency per variant,
   not quality alone.
4. Check sample size and score variance before treating a difference between
   variants as meaningful.
5. Recommend a winner with explicit quality/cost trade-offs, and flag when
   the result is close enough that either variant is defensible.

## References

- `zworkforce/evaluation_suite.py`
- `zworkforce/evaluator.py`
- `examples/evaluation.tiers.json`
- `tests/test_skills_evaluator.py`

## Output

Report the task set, variants compared, per-variant quality/cost/latency,
statistical confidence, and the recommended strategy with trade-offs.
