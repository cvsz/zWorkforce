# ADR 0001: Adopt Transactional Modular Platform Architecture

- Status: Accepted
- Date: 2026-08-14

## Context

The imported application couples HTTP handlers, Facebook operations, scheduling, and JSON-file persistence. That cannot provide transactional approval, idempotent publication, durable orchestration, or horizontal workers.

## Decision

Zeto will use a modular service architecture with a versioned `/v1` API, PostgreSQL repositories, durable background jobs, provider interfaces, object storage, and OpenTelemetry-compatible observability. Migration will proceed as independently deployable vertical slices while compatibility routes are temporary.

## Consequences

Schema changes require migrations. Publishing and generation providers require contract tests. Every workflow mutation must create an audit event. JSON storage must be removed from business logic before Phase 1 can be considered complete.
