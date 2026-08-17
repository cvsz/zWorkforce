# Planning & Implementation: ZSP AI Studio & Video Rendering (`planning-implementation-zsp-aitool.md`)

**Updated:** 2026-08-17T05:25Z (do-all-e2e + do-implementation-all-e2e cycle)  
**Module:** `packages/zsp-aitool/` HyperFrames Video Studio, Next.js 15.5 App Router, and Shopee OCR Pipeline  
**Parent Strategy:** [`exec-planning.master.md`](exec-planning.master.md) & [`exec-planning.zsp-aitool.md`](exec-planning.zsp-aitool.md)

---

## 1. Module Overview & Architecture

`zsp-aitool` provides the visual studio frontend and batch video rendering pipeline on port `:3005` (`studio.zeaz.dev`):

```mermaid
graph TD
    subgraph "Studio Frontend (Next.js 15.5 App Router)"
        STUDIO_UI["HyperFrames Point-Cloud Canvas & Studio UI"]
        SIDEBAR["Asset Sidebar & Multi-scene Timeline"]
        AUDIT_PANEL["Admin Audit & Telemetry Panel"]
    end

    subgraph "Media & Ingestion Pipeline"
        SHOPEE_OCR["Shopee OpenAPI & Product OCR Ingestion"]
        PROMPT_COMPILER["Preset-Enhanced Video Prompt Compiler"]
        RENDER_QUEUE["Batch Video Render Queue & Watchdog"]
    end

    subgraph "Storage & Control Plane"
        PG_SCHEMA["PostgreSQL Data Model (Prisma)"]
        CONTROL_PLANE["zWorkforce Control Plane (:9569)"]
    end

    STUDIO_UI --> PROMPT_COMPILER
    SIDEBAR --> SHOPEE_OCR
    PROMPT_COMPILER --> RENDER_QUEUE
    RENDER_QUEUE --> CONTROL_PLANE
    STUDIO_UI --> PG_SCHEMA
    AUDIT_PANEL --> PG_SCHEMA
```

---

## 2. Completed Implementation Milestones

- [x] **Next.js 15.5 App Router Architecture**: `AppLayout`, `Sidebar`, `Header`, and responsive mobile nav.
- [x] **HyperFrames Video Studio Foundation**: Multi-scene scene breakdown, prompt compiler, and render queue models.
- [x] **Shopee API Product Ingestion & Vision OCR**: Automated product metadata extraction and image OCR text processing.
- [x] **Prisma Multi-Tenant Data Layer**: Full schema with tenant boundaries and audit trail.
- [x] **Batch Export Pipeline & S3 Delivery (Phase 3)**:
  - Built `packages/zsp-aitool/src/services/export_pipeline.ts` with async job queuing and HMAC-signed delivery receipts (`rcpt-*`).
  - Unit tests in `packages/zsp-aitool/tests/export_pipeline.test.js`.
- [x] **Studio Real-Time Collaboration (Phase 4)**:
  - Built `packages/zsp-aitool/src/server/collab_server.js` providing `CollabServer` and `CollabRoom` for multi-user timeline editing with tenant isolation and presence cursor sync.
  - Unit tests in `packages/zsp-aitool/tests/collab_server.test.js`.

---

## 3. Active & Upcoming Implementation Workstreams

### Phase 1: OpenRouter Multimodal Video Generation Engine
- **Objective**: Text-to-video and Image-to-video (first/last frame conditioning) integration with async webhook notifications.
- **Files**:
  - `packages/zsp-aitool/src/services/video_generator.ts`: Multi-scene video generation service.
  - `packages/zsp-aitool/src/app/api/webhooks/video/route.ts`: HMAC-verified webhook handler.

### Phase 2: HyperFrames Keyframe Composition & Audio Sync
- **Objective**: Multi-layer timeline canvas with real-time waveform audio alignment and text animation overlays.
- **Files**:
  - `packages/zsp-aitool/src/components/studio/TimelineCanvas.tsx`: WebGL/HTML5 canvas timeline.

## 4. Verification & Validation Protocol

```bash
# 1. Next.js Studio Build & Test
pnpm --dir packages/zsp-aitool test
pnpm --dir packages/zsp-aitool build
```
