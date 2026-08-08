# Threat Model

Trust boundaries: client→API, API→database, runtime→provider, model output→tool gateway, tool gateway→filesystem/network/process.

Controls address prompt-injection-to-tools, credential exfiltration, runaway compute, unauthorized mutation, path traversal, command injection, SSRF and replay. App-level audit is append-only through public APIs; high-assurance deployments should export audit events to an immutable external sink. Network-layer egress controls remain recommended to mitigate DNS rebinding and provider/tool compromise.
