#!/usr/bin/env python3
"""
Z.A.R.V.I.S. voice-agent health check.

Exits 0 if the agent port is reachable. When VOICE_AGENT_REPORT_PROVIDERS=1,
also emits a JSON health summary of registered speech providers to stdout.
No provider credentials or audio data are ever written to stdout.
"""
import json
import os
import socket
import sys

host = os.getenv("VOICE_AGENT_HEALTH_HOST", "127.0.0.1")
port = int(os.getenv("VOICE_AGENT_PORT", "8765"))
report_providers = os.getenv("VOICE_AGENT_REPORT_PROVIDERS", "").strip() in {"1", "true", "yes"}

try:
    with socket.create_connection((host, port), timeout=3):
        pass
except OSError:
    sys.exit(1)

if report_providers:
    try:
        # Import lazily so the healthcheck can run without the full voice-agent env.
        from speech.registry import get_registry  # type: ignore[import]
        summary = get_registry().health_summary()
        print(json.dumps({"voice_agent": "ok", "speech_providers": summary}))
    except ImportError:
        print(json.dumps({"voice_agent": "ok", "speech_providers": "unavailable"}))
