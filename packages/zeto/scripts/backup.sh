#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
backup_dir=${BACKUP_DIR:-./backups}
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
umask 077
mkdir -p "$backup_dir"
output="$backup_dir/zeto-$timestamp.dump"

pg_dump --format=custom --no-owner --no-acl --file="$output" "$DATABASE_URL"
sha256sum "$output" > "$output.sha256"
printf '%s\n' "$output"

