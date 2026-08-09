#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${ZWORKFORCE_BASE_URL:-http://127.0.0.1:9569}"
CURL=(curl --fail --silent --show-error --connect-timeout 5 --max-time 15)

check_json_field() {
  local url="$1" field="$2" expected="$3"
  local body
  body="$("${CURL[@]}" "$url")"
  python - "$field" "$expected" <<'PY' <<<"$body"
import json, sys
field, expected = sys.argv[1], sys.argv[2]
data = json.load(sys.stdin)
actual = data
for part in field.split('.'):
    actual = actual[part]
if str(actual).lower() != expected.lower():
    raise SystemExit(f"{field}={actual!r}, expected {expected!r}")
PY
}

check_json_field "${BASE_URL}/health" status ok
"${CURL[@]}" "${BASE_URL}/ready" >/dev/null

if [[ -n "${ZWORKFORCE_API_KEY:-}" ]]; then
  "${CURL[@]}" \
    -H "Authorization: Bearer ${ZWORKFORCE_API_KEY}" \
    "${BASE_URL}/api/v1/overview" >/dev/null
fi

echo "smoke test passed: ${BASE_URL}"
