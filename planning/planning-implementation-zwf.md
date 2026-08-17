# Planning & Implementation: zWorkforce Core Control Plane (`planning-implementation-zwf.md`)

**Updated:** 2026-08-17T05:25Z (do-all-e2e + do-implementation-all-e2e cycle)
**Module:** `zworkforce/` Python Control Plane, DB Repository, Distributed Task Queue, and Auth Gateway  
**Parent Strategy:** [`exec-planning.master.md`](exec-planning.master.md) & [`exec-planning-zwf.md`](exec-planning-zwf.md)

---

## 1. Module Overview & Architecture

`zworkforce` provides the production-grade control plane for multi-tenant AI workforce orchestration:

```mermaid
graph TD
    subgraph "Core Ingestion & Auth"
        API["FastAPI / HTTP & WebSocket Gateway (:9569)"]
        AUTH["Bearer Token / Scope / HMAC Signature Verifier"]
        GOV["Governance & Immutable Audit Ledger"]
    end

    subgraph "Execution & Queue Plane"
        QUEUE["Distributed Transactional Queue (SQLite / PostgreSQL)"]
        DOOM_GUARD["Doom Loop Cycle Detector (Signature Tracking)"]
        OUTBOX["Reliable Webhook Outbox Worker (X-Delivery-ID)"]
        ENGINE["Execution Engine & Tool Dispatcher"]
    end

    subgraph "Tooling & Connectors"
        TOOLS["Standard Tools (File, Shell, Command)"]
        CONNECTORS["Omnichannel Connectors (Shopee, TikTok, Meta)"]
        MCP_SERVER["MCP 2026-07-28 Stateless Endpoint (/mcp)"]
        ACP_SERVER["Agent Client Protocol Endpoint (/acp)"]
    end

    API --> AUTH
    AUTH --> GOV
    API --> QUEUE
    QUEUE --> DOOM_GUARD
    DOOM_GUARD --> ENGINE
    ENGINE --> TOOLS
    ENGINE --> CONNECTORS
    ENGINE --> OUTBOX
    API --> MCP_SERVER
    API --> ACP_SERVER
```

---

## 2. Completed Implementation Milestones

- [x] **Durable Multi-Tenant Database Repository**:
  - Schema evolution with PostgreSQL session advisory locks and SQLite fallback (`zworkforce/db.py`, `zworkforce/db_migrations.py`).
  - Immutable cryptographic hash chain for audit events (`zworkforce/db_governance.py`).
- [x] **Automatic Doom-Loop Detection Engine (R8.2)**:
  - Tracks sorted tool call signatures and consecutive failure counters in `zworkforce/engine.py`.
  - Configurable thresholds (`doom_loop_max_identical_calls`, `doom_loop_max_consecutive_failures`) in `zworkforce/config.py`.
- [x] **Omnichannel Social & Shop Connectors**:
  - Built `zworkforce/connectors.py` supporting Shopee Open Platform v2, TikTok Shop Seller API, and Facebook Commerce.
  - Implemented HMAC-SHA256 signature verification and fail-closed approval governance.
- [x] **Slash Command Interactive Navigation (SW2/SW11)**:
  - Interactive popup autocomplete menu and contextual documentation hints in web static frontend (`index.html`, `app.js`, `styles.css`).
- [x] **Standalone Test Runner Import Fix (PR #110)**:
  - Added `try/except ImportError` fallback for `tests.common` import in `tests/test_connectors.py`.
  - Enables canonical `PYTHONPATH=. python3 -m unittest tests/test_connectors.py -v` to pass per `AGENTS.md`.

---

## 3. Active & Upcoming Implementation Workstreams

### Phase 1: Secure MCP Reverse Tunnel Client Gateway
- **Objective**: Allow localhost / private edge MCP servers to securely connect to cloud workforce without inbound ports.
- **Files to Implement/Touch**:
  - `zworkforce/tunnel.py`: Reverse-tunnel client using encrypted WebSockets and ephemeral ticket auth.
  - `zworkforce/api.py`: Endpoint `POST /api/v1/mcp/tunnel/connect`.
  - `tests/test_tunnel.py`: Unit test suite verifying tunnel handshake, heartbeat, and tool forwarding.

### Phase 2: Agent Client Protocol (ACP) Multi-IDE Integration
- **Objective**: Expose full ACP JSON-RPC standard for Cursor, VS Code, and Zed editor companion integration.
- **Files to Implement/Touch**:
  - `zworkforce/acp.py`: Bidirectional ACP server with standard operations (`initialize`, `newSession`, `prompt`, `cancel`, `requestPermission`).
  - `tests/test_acp.py`: ACP compliance test suite.

### Phase 3: OTLP Telemetry & Multi-Sink Trace Export
- **Objective**: Programmatic trace export to OpenTelemetry Collector, Langfuse, Grafana Cloud, Arize AX.
- **Files to Implement/Touch**:
  - `zworkforce/telemetry.py`: OTLP span processor, token counter histogram, and provider attribution metadata.
  - `tests/test_telemetry.py`: Unit tests verifying span structure and no-credential export invariants.

### Phase 4: Typed Agent Handoff & Guardrail Protocol
- **Objective**: Multi-agent routing with typed input/output validation, context compaction, and deterministic tool call evaluation on zero-cost free model tiers.
- **Files to Implement/Touch**:
  - `zworkforce/agent_handoff.py`: Typed handoff contracts, context window budgets, and escalation guards.
  - `tests/test_agent_handoff.py`: Context isolation and cross-agent boundary tests.

---

## 4. Quality & Verification Gates

```bash
# 1. Bytecode Compilation & Unit Tests
python3 -m compileall -q zworkforce tests
PYTHONPATH=. python3 -m unittest discover -s tests -v

# 2. System Health Doctor
zworkforce doctor

# 3. PostgreSQL Concurrency & Regression
PYTHONPATH=. python3 -m unittest tests/test_v3_postgres.py -v
```
