#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK="${CLOUDFLARE_STACK_DIR:-$ROOT/infrastructure/terraform/cloudflare}"
BACKUP_DIR="${CLOUDFLARE_STATE_BACKUP_DIR:-$ROOT/output/backups}"
ENV_FILE="${CLOUDFLARE_ENV_FILE:-$ROOT/.env.cloudflare}"
COMMAND="${1:-verify}"

case "$COMMAND" in
  init|migrate|verify) ;;
  *) echo "Usage: $0 {init|migrate|verify}" >&2; exit 2 ;;
esac

[[ -f "$ENV_FILE" && ! -L "$ENV_FILE" ]] || {
  echo "Cloudflare environment must be a regular file: $ENV_FILE" >&2
  exit 1
}
mode="$(stat -c '%a' "$ENV_FILE")"
(( (8#$mode & 8#077) == 0 )) || {
  echo "Cloudflare environment must not be group/world accessible: $ENV_FILE" >&2
  exit 1
}

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

[[ "${TERRAFORM_BACKEND_TYPE:-}" == "r2" ]] || {
  echo "TERRAFORM_BACKEND_TYPE must be r2" >&2
  exit 1
}
for key in CLOUDFLARE_ACCOUNT_ID TERRAFORM_STATE_BUCKET \
  CLOUDFLARE_S3_API_ENDPOINT CLOUDFLARE_ACCESS_KEY_ID \
  CLOUDFLARE_ACCESS_SECRET_KEY; do
  [[ -n "${!key:-}" ]] || { echo "Missing $key in $ENV_FILE" >&2; exit 1; }
done
[[ "$TERRAFORM_STATE_BUCKET" =~ ^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$ ]] || {
  echo "TERRAFORM_STATE_BUCKET is not a valid private R2 bucket name" >&2
  exit 1
}
expected_endpoint="https://${CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"
[[ "${CLOUDFLARE_S3_API_ENDPOINT%/}" == "$expected_endpoint" ]] || {
  echo "CLOUDFLARE_S3_API_ENDPOINT must be the current account R2 endpoint" >&2
  exit 1
}

TF_BIN="${TERRAFORM_BIN:-$ROOT/tools/bin/terraform}"
command -v "$TF_BIN" >/dev/null || { echo "Terraform not found" >&2; exit 1; }
export AWS_ACCESS_KEY_ID="$CLOUDFLARE_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$CLOUDFLARE_ACCESS_SECRET_KEY"
export AWS_REGION=auto AWS_DEFAULT_REGION=auto
export AWS_EC2_METADATA_DISABLED=true TF_IN_AUTOMATION=1 TF_INPUT=0

backend_config="$(mktemp "$STACK/.backend.XXXXXX.hcl")"
remote_state="$(mktemp "$STACK/.remote-state.XXXXXX.json")"
before_addresses="$(mktemp "$STACK/.state-before.XXXXXX.txt")"
after_addresses="$(mktemp "$STACK/.state-after.XXXXXX.txt")"
backend_template="$STACK/backend.r2.tf.example"
backend_file="$STACK/backend.tf"
backend_created=false
backend_initialized=false
cleanup() {
  status=$?
  rm -f "$backend_config" "$remote_state" "$before_addresses" "$after_addresses"
  if (( status != 0 )) && [[ "$backend_created" == "true" && "$backend_initialized" != "true" ]]; then
    rm -f "$backend_file"
  fi
  return "$status"
}
trap cleanup EXIT
chmod 600 "$backend_config" "$remote_state" "$before_addresses" "$after_addresses"
printf 'bucket = "%s"\nendpoints = { s3 = "%s" }\n' \
  "$TERRAFORM_STATE_BUCKET" "$expected_endpoint" > "$backend_config"
[[ -f "$backend_template" ]] || {
  echo "Canonical R2 backend template is missing" >&2
  exit 1
}
install_backend() {
  if [[ -e "$backend_file" ]]; then
    cmp -s "$backend_template" "$backend_file" || {
      echo "Installed backend.tf differs from the canonical R2 template" >&2
      exit 1
    }
  else
    install -m 600 "$backend_template" "$backend_file"
    backend_created=true
  fi
}

if [[ "$COMMAND" == "migrate" ]]; then
  [[ "${ALLOW_R2_WRITE:-false}" == "true" ]] || {
    echo "ALLOW_R2_WRITE must be true for state migration" >&2
    exit 1
  }
  local_state="$STACK/terraform.tfstate"
  [[ -f "$local_state" && ! -L "$local_state" && -s "$local_state" ]] || {
    echo "Local Terraform state is missing; refusing an empty migration" >&2
    exit 1
  }
  state_mode="$(stat -c '%a' "$local_state")"
  (( (8#$state_mode & 8#077) == 0 )) || {
    echo "Local Terraform state must not be group/world accessible" >&2
    exit 1
  }
  python3 - "$local_state" <<'PY'
import json
import pathlib
import sys

state = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
if not isinstance(state, dict) or state.get("version") != 4:
    raise SystemExit("Local Terraform state is not a version 4 state object")
if not isinstance(state.get("lineage"), str) or not state["lineage"]:
    raise SystemExit("Local Terraform state has no lineage")
if not isinstance(state.get("resources"), list) or not state["resources"]:
    raise SystemExit("Local Terraform state has no managed resources")
PY
  "$TF_BIN" -chdir="$STACK" state list -state="$local_state" > "$before_addresses"
  [[ -s "$before_addresses" ]] || {
    echo "Local Terraform state has no managed resources" >&2
    exit 1
  }
  [[ ! -L "$BACKUP_DIR" ]] || {
    echo "Cloudflare state backup directory must not be a symlink" >&2
    exit 1
  }
  install -d -m 700 "$BACKUP_DIR"
  backup="$(mktemp "$BACKUP_DIR/cloudflare-state-$(date -u +%Y%m%dT%H%M%SZ).XXXXXX.tfstate")"
  install -m 600 "$local_state" "$backup"
  (
    cd "$BACKUP_DIR"
    sha256sum "$(basename "$backup")" > "$(basename "$backup").sha256"
  )
  chmod 600 "$backup.sha256"
  install_backend
  "$TF_BIN" -chdir="$STACK" init -migrate-state -force-copy \
    -backend-config="$backend_config"
  backend_initialized=true
else
  install_backend
  "$TF_BIN" -chdir="$STACK" init -reconfigure \
    -backend-config="$backend_config"
  backend_initialized=true
fi

"$TF_BIN" -chdir="$STACK" state pull > "$remote_state"
python3 - "$remote_state" "${backup:-}" <<'PY'
import json
import pathlib
import sys

state = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
if not isinstance(state, dict) or state.get("version") != 4:
    raise SystemExit("Remote Terraform state is not a version 4 state object")
if not isinstance(state.get("resources"), list) or not state["resources"]:
    raise SystemExit("Remote Terraform state has no managed resources")
if sys.argv[2]:
    local = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
    if state.get("lineage") != local.get("lineage"):
        raise SystemExit("Remote Terraform state lineage differs from the local backup")
PY
"$TF_BIN" -chdir="$STACK" state list > "$after_addresses"
[[ -s "$after_addresses" ]] || {
  echo "Remote Terraform state has no managed resource addresses" >&2
  exit 1
}
if [[ "$COMMAND" == "migrate" ]]; then
  diff -u "$before_addresses" "$after_addresses"
fi
echo "Cloudflare R2 state $COMMAND verification passed."
