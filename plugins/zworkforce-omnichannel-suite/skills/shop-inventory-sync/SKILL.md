---
name: shop-inventory-sync
description: Synchronize product catalog variants, pricing, and warehouse inventory levels across Shopee Seller, TikTok Shop, and Facebook Commerce.
---

# Shop Inventory & Price Sync Skill

## Purpose
Ensures consistent product catalog data, prevents overselling during flash sales, and enforces price drop guardrails across multiple e-commerce storefronts.

## Workflow Steps:
1. **Inventory & Price Audit**:
   - Fetch real-time available stock levels using `shop_connector`.
2. **Price Change Delta Guard**:
   - Verify that proposed price changes do not exceed configured max allowable delta (e.g. max 20% discount without manager approval).
3. **Approval Escalation**:
   - Require explicit four-eyes approval for batch price reductions or inventory write-downs.
4. **Atomic Multi-Store Update**:
   - Execute updates using platform-specific HMAC-SHA256 signatures for Shopee OpenAPI v2 and TikTok Shop Seller API.
