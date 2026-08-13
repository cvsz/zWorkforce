# Health Check Matrix

| Service | Endpoint | Expected result | Does not verify |
|---|---|---|---|
| zarvis-orchestrator | `GET /health` | process reachable; command runtime configured | upstream GitHub availability |
| zarvis-task-gateway | `GET /healthz` | process reachable; durable task runtime configured | worker execution success |
| voice-gateway | `GET /health` | process reachable; session limits configured | model runtime health |
| voice-agent | `GET /health` | process reachable; speech runtime configured | browser microphone access |

Health endpoints are unauthenticated only because they expose no secrets, job data, tenant data, or provider configuration values.

Use readiness checks separately once an operator selects durable storage, queue, and observability backends.
