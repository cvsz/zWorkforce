---
name: order-fulfillment-ops
description: Ingest, triage, and update order statuses across Shopee Open Platform, TikTok Shop, and Meta Commerce Checkout.
---

# Order Fulfillment & Operations Skill

## Purpose
Provides automated order status tracking, shipping SLA monitoring, and customer support notification triggers.

## Workflow Steps:
1. **Order Polling**:
   - Query pending and unfulfilled orders across Shopee, TikTok Shop, and Facebook Commerce.
2. **SLA Deadlines**:
   - Calculate shipping deadlines and prioritize orders nearing SLA breaches.
3. **Audit Trail**:
   - Persist fulfillment events into tenant-isolated audit logs.
