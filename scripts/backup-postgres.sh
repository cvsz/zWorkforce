#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ -z "${ZWORKFORCE_DATABASE_URL:-}" ]]; then
  echo "ZWORKFORCE_DATABASE_URL is required" >&2
  exit 2
fi

for command in pg_dump pg_restore sha256sum; do
  command -v "$command" >/dev/null 2>&1 || { echo "$command is required" >&2; exit 2; }
done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${ZWORKFORCE_BACKUP_DIR:-./backups}"
OUTPUT="${1:-${BACKUP_DIR}/zworkforce-${STAMP}.dump}"
mkdir -p "$(dirname "$OUTPUT")"

TMP="${OUTPUT}.partial"
rm -f "$TMP"
trap 'rm -f "$TMP"' EXIT

pg_dump \
  --format=custom \
  -Z 9 \
  --no-owner \
  --no-acl \
  --file "$TMP" \
  "$ZWORKFORCE_DATABASE_URL"

# A backup is not accepted until pg_restore can parse its catalog.
pg_restore --list "$TMP" >/dev/null
mv "$TMP" "$OUTPUT"
trap - EXIT
sha256sum "$OUTPUT" > "${OUTPUT}.sha256"

printf 'backup=%s\nchecksum=%s\n' "$OUTPUT" "${OUTPUT}.sha256"
