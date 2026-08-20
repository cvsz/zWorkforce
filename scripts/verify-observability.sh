#!/bin/bash
set -euo pipefail
# Shim: delegate to scripts/release/verify-observability.sh for Stage G evidence.
exec "$(dirname "${BASH_SOURCE[0]}")/release/verify-observability.sh" "$@"
