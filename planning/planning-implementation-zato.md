# Planning & Implementation: Zeto AI Content Factory (`planning-implementation-zato.md`)

**Updated:** 2026-08-17T05:25Z (do-all-e2e + do-implementation-all-e2e cycle)
**Module:** `packages/zeto/` Content Lifecycle Engine (`IDEATE → GENERATE → WRITE → APPROVE → PUBLISH → MONITOR → LEARN`)  
**Parent Strategy:** [`exec-planning.master.md`](exec-planning.master.md) & [`exec-planning-zato.md`](exec-planning-zato.md)

---

## 1. Module Overview & Architecture

Zeto operates the enterprise content factory combining ProMeta prompt compilers, 12-point QA scorecards, and multi-channel publishing adapters:

```mermaid
graph LR
    IDEATE["1. Strategy & Ideation (M01)"] --> GENERATE["2. AI Image & Video (M02/M03)"]
    GENERATE --> WRITE["3. Captions & Hooks (M05)"]
    WRITE --> QA["4. 12-Point QA Scorecard (M10)"]
    QA --> APPROVAL["5. Human Approval Gate"]
    APPROVAL --> PUBLISH["6. Omnichannel Publisher (M06)"]
    PUBLISH --> MONITOR["7. Social Listening (M07)"]
    MONITOR --> LEARN["8. Optimization Loop"]
    LEARN --> IDEATE
```

---

## 2. Completed Implementation Milestones

- [x] **ProMeta Prompt Compiler Architecture**: Multi-mode execution (`PRODUCTION`, `OPS`, `OPTIMIZE`, `REVIEW`).
- [x] **Omnichannel Multi-Platform Publisher**:
  - Social adapters: Facebook Pages/Groups, Instagram Graph, TikTok Content, YouTube Data API, X (Twitter) v2, LinkedIn Marketing.
  - Shop adapters: Shopee Open Platform v2, TikTok Shop Seller API, Facebook Commerce Catalog.
- [x] **Cryptographic Verification**: HMAC-SHA256 partner key signing for Shopee OpenAPI v2 and TikTok Shop.
- [x] **Universal Plugin Packaging**: Packaged as `zworkforce-omnichannel-suite` with skills for content publishing, shop inventory sync, and order operations.
- [x] **Automated 12-Point QA Self-Correction Loop (Phase 1)**:
  - Built `packages/zeto/src/domain/qa_engine.js` scoring hook clarity, brand voice, safe margins, claim substantiation, and CTAs with auto-remediation.
  - Unit tests in `packages/zeto/test/qa_seo_engine.test.js`.
- [x] **SEO & Platform Algorithm Keyword Injection (Phase 3)**:
  - Built `packages/zeto/src/domain/seo_engine.js` with per-platform keyword density and hashtag policies (Shopee, TikTok, Meta, YouTube).
  - Unit tests in `packages/zeto/test/qa_seo_engine.test.js`.

---

## 3. Active & Upcoming Implementation Workstreams

### Phase 2: Live Performance Feedback & Prompt Tuning
- **Objective**: Ingest social engagement metrics (views, shares, retention rate) and automatically recalibrate ProMeta prompt weights.
- **Files**:
  - `packages/zeto/src/feedback_optimizer.ts`: Retention curve analytics and prompt re-weighting.

### Phase 4: Approval Gate & Human-in-Loop Escalation
- **Objective**: Wiring the 12-point QA scorecard into the zWorkforce approval gate (`approval_requests` table) with auto-escalation for scores below 90.
- **Files**:
  - `packages/zeto/src/approval_gateway.ts`: Approval request creation and webhook trigger.
  - `zworkforce/api.py`: `POST /api/v1/approval/decide` endpoint for approve/reject.
  - `tests/test_approval.py`: Approval lifecycle and cross-tenant isolation tests.

---

## 4. Verification & Validation Protocol

```bash
# 1. Zeto Test Suite
pnpm --dir packages/zeto test

# 2. Control Plane Connectors Unit Test
PYTHONPATH=. python3 -m unittest tests/test_connectors.py -v
```
