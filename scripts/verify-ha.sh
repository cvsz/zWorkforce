#!/usr/bin/env bash
set -euo pipefail
# Shim: delegate to scripts/release/verify-ha.sh for Stage E evidence.
exec "$(dirname "${BASH_SOURCE[0]}")/release/verify-ha.sh" "$@"