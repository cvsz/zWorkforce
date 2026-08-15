#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL must identify a disposable verification database}"
: "${1:?usage: verify-backup.sh BACKUP_FILE}"

if [ "$DATABASE_URL" = "$RESTORE_DATABASE_URL" ]; then
  printf '%s\n' "Refusing to restore into the source database" >&2
  exit 2
fi

backup=$1
test -f "$backup"
test -f "$backup.sha256"
sha256sum --check "$backup.sha256"
pg_restore --clean --if-exists --no-owner --no-acl --dbname="$RESTORE_DATABASE_URL" "$backup"
psql "$RESTORE_DATABASE_URL" -v ON_ERROR_STOP=1 -Atqc \
  "SELECT CASE WHEN to_regclass('public.migrations') IS NOT NULL AND to_regclass('public.workflow_runs') IS NOT NULL THEN 'restore-ok' ELSE 'restore-invalid' END" \
  | grep -qx restore-ok
printf '%s\n' "restore verification passed"

