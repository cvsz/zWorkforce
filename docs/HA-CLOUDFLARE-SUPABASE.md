# HA-A Cloudflare + HA-B Supabase

## Production topology

zWorkforce uses two complementary HA boundaries rather than treating Supabase as a replacement application runtime.

- **HA-A — Cloudflare:** public DNS, proxied edge, Cloudflare Tunnel, access controls, and optional managed tunnel configuration. The canonical public zWorkforce endpoint is `https://zwf.zeaz.dev`.
- **HA-B — Supabase:** durable PostgreSQL and Supabase Storage data plane. Production project ref: `qhprcfdgajhmdzvnsffb` (`zWorkforce`, `ap-northeast-1`). Project API URL: `https://qhprcfdgajhmdzvnsffb.supabase.co`.
- **Runtime HA:** a second zWorkforce runtime is still required for application-runtime active/passive failover. Supabase is not an HTTP origin substitute for the zWorkforce API.
- **Semantic memory:** Qdrant remains the vector-memory backend when configured; this HA change does not migrate semantic memory to pgvector.

## Canonical HA-A routes

| Public host | Loopback origin | Role |
| --- | --- | --- |
| `zwf.zeaz.dev` | `http://127.0.0.1:9570` | zWorkforce API/control plane |
| `studio.zeaz.dev` | `http://127.0.0.1:3005` | ZSP AI Studio |
| `zarvis.zeaz.dev` | `http://127.0.0.1:9570` | governed Z.A.R.V.I.S. gateway |
| `zider.zeaz.dev` | `http://127.0.0.1:8085` | zider BFF |

These mappings are declared in `infrastructure/terraform/cloudflare/zworkforce.tf`, included in the optional managed tunnel configuration in `main.tf`, and mirrored by `deploy/cloudflare/tunnel-ingress.yml`. CI fails if these copies drift.

`MANAGE_TUNNEL_CONFIG` remains `false` in automated production jobs. This is deliberate: the existing shared tunnel must first be imported into Terraform state and reviewed before Terraform is authorized to replace its complete ingress configuration. DNS reconciliation and apply remain automated without weakening that guard.

## HA-B Supabase production state

The connected production project is healthy and uses PostgreSQL 17. The existing Supabase Storage bucket is named `zworkforce`.

The GitHub production workflow performs a read-only PostgreSQL preflight before any Cloudflare apply:

```sql
select 1;
```

Use the Supabase Postgres connection string as `SUPABASE_DATABASE_URL` in the GitHub `production` Environment. Application deployments should supply the same managed connection through `ZWORKFORCE_DATABASE_URL`; do not commit the password or connection string.

Supabase Storage credentials are intentionally not generated or committed by this repository. Where the zWorkforce S3 artifact adapter is used with Supabase Storage's S3-compatible interface, store endpoint/access credentials only in the deployment secret boundary and map them to the existing `ZWORKFORCE_S3_*` settings.

## GitHub Environment secrets

Create a protected GitHub Environment named `production` and set these secrets:

| Secret | Purpose |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` | scoped DNS/Tunnel API token |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account containing the tunnel |
| `CLOUDFLARE_ZONE_ID` | `zeaz.dev` zone ID |
| `CLOUDFLARE_TUNNEL_ID` | existing tunnel UUID |
| `PIEWDASH_ACCESS_ALLOWED_EMAILS` | JSON array required by the existing Access policy |
| `CLOUDFLARE_TF_STATE_BUCKET` | private R2 Terraform-state bucket |
| `CLOUDFLARE_R2_S3_ENDPOINT` | R2 S3 API endpoint |
| `CLOUDFLARE_R2_ACCESS_KEY_ID` | bucket-scoped state key |
| `CLOUDFLARE_R2_SECRET_ACCESS_KEY` | bucket-scoped state secret |
| `SUPABASE_DATABASE_URL` | TLS Supabase Postgres connection string |

The workflow materializes these values only into a mode-`0600` ignored `.env.cloudflare` file on the ephemeral runner and removes it in an `always()` cleanup step.

## Automated flow

`.github/workflows/ha-infrastructure.yml` implements:

1. **Every relevant PR:** Terraform format, backend-free init, validate, and canonical route drift checks. No production secrets are required.
2. **Manual `plan`:** protected `production` Environment, Supabase DB preflight, R2-backed Terraform state, Cloudflare DNS reconciliation/import, then saved Terraform plan.
3. **Manual `apply`:** same preflights and state controls, followed by apply and a public `https://zwf.zeaz.dev/health` smoke check.
4. **Failure behavior:** missing secrets, unavailable Supabase, Terraform drift/validation failure, DNS ambiguity, or state/backend errors stop the workflow before mutation.

## Enabling full tunnel ownership

Do not set `MANAGE_TUNNEL_CONFIG=true` merely to make the workflow more automatic. First import the existing `cloudflare_zero_trust_tunnel_cloudflared_config` resource into the authoritative R2-backed state, compare every live ingress entry with Terraform, and confirm the final catch-all rule. The existing `scripts/cloudflare-apply.sh` guard refuses tunnel management if that imported state evidence is absent.

After that one-time adoption is complete, `MANAGE_TUNNEL_CONFIG=true` can be promoted through the same protected environment so Cloudflare DNS and tunnel ingress are both controlled by Terraform.

## Runtime active/passive extension

For true application-runtime failover, deploy a second zWorkforce API/worker/scheduler stack against the same managed HA-B data plane, give each runtime an independently monitored origin, and place them behind Cloudflare Load Balancing as primary/secondary pools. Do not point the secondary pool directly at Supabase; it must be another zWorkforce runtime implementing the same API and health contract.
