---
name: zworkforce-webhook-outbox
description: Operate the zWorkforce durable webhook outbox, including HMAC signatures, retry/backoff, dedupe, and active/passive leader election across replicas.
---

# zWorkforce Webhook Outbox Operations

Deliver external side effects exactly once in effect, even across restarts
and multiple replicas.

## Workflow

1. Confirm which event types are enqueued to the outbox and which endpoints
   they are destined for.
2. Verify every outbound delivery is HMAC-signed and the receiving side can
   validate the signature.
3. Check retry/backoff behavior on failure: attempts are bounded, spaced
   correctly, and failed deliveries are surfaced rather than silently
   dropped.
4. Confirm only the current leader replica dispatches from the outbox at a
   time, and that leadership handoff does not duplicate or drop in-flight
   deliveries.
5. Trace a delivery from enqueue through signed dispatch to acknowledged
   receipt before declaring the outbox path healthy.

## References

- `zworkforce/outbox.py`
- `docs/OPERATIONS.md`
- `README.md` webhook outbox section

## Output

Report enqueue-to-delivery evidence, signature verification status, retry
behavior, leader-election correctness, and any duplicate or dropped
deliveries found.
