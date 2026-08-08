# Operations

- `/health`: process liveness.
- `/ready`: runtime configuration loaded.
- `/metrics`: authenticated Prometheus metrics.
- `python -m zworkforce doctor`: storage/config summary.

For cost spikes inspect model mix, top agents, iterations and budgets, then right-size tiers/limits. Interrupted queued/running tasks are requeued on restart. Provider failures are bounded and fail closed rather than silently consuming unlimited compute.
