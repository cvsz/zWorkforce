#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <backup.dump>" >&2
  exit 2
fi
if [[ -z "${ZWORKFORCE_DATABASE_URL:-}" ]]; then
  echo "ZWORKFORCE_DATABASE_URL is required" >&2
  exit 2
fi
if [[ "${ZWORKFORCE_RESTORE_CONFIRM:-}" != "YES" ]]; then
  echo "refusing restore: set ZWORKFORCE_RESTORE_CONFIRM=YES after stopping API/workers/schedulers/outbox" >&2
  exit 2
fi

for command in pg_restore sha256sum; do
  command -v "$command" >/dev/null 2>&1 || { echo "$command is required" >&2; exit 2; }
done

BACKUP="$1"
[[ -f "$BACKUP" ]] || { echo "backup not found: $BACKUP" >&2; exit 2; }

if [[ -f "${BACKUP}.sha256" ]]; then
  sha256sum --check "${BACKUP}.sha256"
else
  echo "warning: checksum sidecar ${BACKUP}.sha256 not found" >&2
fi

# Validate the archive before touching the target database.
pg_restore --list "$BACKUP" >/dev/null

pg_restore \
  --exit-on-error \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --dbname "$ZWORKFORCE_DATABASE_URL" \
  "$BACKUP"

echo "restore completed; run zworkforce doctor and scripts/smoke-test.sh before resuming traffic"
