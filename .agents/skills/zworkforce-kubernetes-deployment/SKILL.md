---
name: zworkforce-kubernetes-deployment
description: Plan and verify zWorkforce Kubernetes deployment including hardened pods, API/worker scaling, PodDisruptionBudgets, persistent artifacts/workspace storage, and default-deny network policy.
---

# zWorkforce Kubernetes Deployment

Ship the control plane to Kubernetes without weakening its security or
availability posture.

## Workflow

1. Identify which manifests are affected: API, worker, scheduler, outbox,
   or shared config/secret resources under `deploy/kubernetes`.
2. Verify pod hardening is preserved: non-root user, read-only root
   filesystem where applicable, dropped capabilities, and resource limits.
3. Confirm default-deny network policy remains in place and any new traffic
   path is explicitly allowlisted, not opened broadly.
4. Verify PodDisruptionBudgets, replica counts, and persistent volume claims
   for artifacts/workspace storage match the durability requirements of the
   affected component.
5. Do not claim a cluster resource, image, or secret exists in the target
   environment without checking it; treat cluster state as external evidence.

## References

- `deploy/kubernetes`
- `docs/DEPLOYMENT.md`
- `Dockerfile`
- `AGENTS.md` architecture rules

## Output

Report which manifests changed, hardening/network-policy verification,
scaling and PDB configuration, and any external cluster evidence still
required before rollout.
