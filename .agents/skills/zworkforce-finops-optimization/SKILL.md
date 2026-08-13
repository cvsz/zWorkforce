---
name: zworkforce-finops-optimization
description: Analyze zWorkforce AI FinOps data including budgets, chargeback, showback, token and credit spend, provider/model tiers, SLO outcomes, rightsizing recommendations, capacity forecasts, and cost per successful outcome.
---

# zWorkforce FinOps Optimization

Optimize for successful outcomes per credit, not raw token minimization.

## Workflow

1. Group spend by tenant, department, agent, provider, model tier, task type,
   workflow, and time window.
2. Compare pass rate, outcome score, latency, retry cost, and SLO compliance.
3. Flag budget burn, inefficient tier selection, provider degradation, and
   low-value automation.
4. Recommend tier/provider changes only when quality evidence supports them.
5. Produce chargeback/showback and capacity forecast outputs with assumptions.

## References

- `zworkforce/economics.py`
- `zworkforce/db_finops.py`
- `zworkforce/evaluation_suite.py`
- `tests/test_v3_rag_artifacts.py`
- `tests/test_v3_scheduler_eval.py`
- `README.md` AI FinOps section

## Output

Return current spend, quality, forecast, recommendation, expected savings,
quality risk, and validation needed before promotion.
