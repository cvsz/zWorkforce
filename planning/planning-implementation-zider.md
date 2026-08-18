# Planning & Implementation: Zider AI Browser Companion (`planning-implementation-zider.md`)

**Updated:** 2026-08-17T18:30Z (auto-quad-loop)  
**Module:** `packages/zider/` Manifest V3 Browser Sidebar, Shadow DOM Isolation, ChatPDF, and YouTube Translator  
**Parent Strategy:** [`exec-planning.master.md`](exec-planning.master.md) & [`exec-planning.zider.md`](exec-planning.zider.md)

---

## 1. Module Overview & Architecture

Zider is an enterprise Manifest V3 browser extension operating on port `:8085`:

```mermaid
graph TD
    subgraph "Browser Content & Sidebar"
        PAGE["Host Web Page (DOM)"]
        SHADOW["Shadow DOM Isolated Sidebar"]
        TOOLBAR["Context Selection Toolbar"]
    end

    subgraph "Extension Background & Bus"
        SW["Service Worker Background Orchestrator"]
        BUS["Chrome Runtime Message Bus"]
        PDF_ENGINE["ChatPDF Vector Indexer & Parser"]
    end

    subgraph "Gateway & Intelligence"
        GATEWAY["Zider Local Gateway (:8085)"]
        GROUP_AI["Group AI Multi-Model Streaming Compare"]
        ZWF_CORE["zWorkforce Model Router (:9569)"]
    end

    PAGE --> TOOLBAR
    TOOLBAR --> BUS
    SHADOW --> BUS
    BUS --> SW
    SW --> PDF_ENGINE
    SW --> GATEWAY
    GATEWAY --> GROUP_AI
    GROUP_AI --> ZWF_CORE
```

---

## 2. Completed Implementation Milestones

- [x] **Shadow DOM Isolation**: Prevents host page CSS and script collisions.
- [x] **Service Worker Message Bus**: Resilient Chrome extension background communication.
- [x] **Group AI Multi-Model Streaming**: Side-by-side comparison of free models (`Llama 3.3`, `DeepSeek-R1`, `Gemini Flash`).
- [x] **ChatPDF Vector Indexing**: Tenant-scoped vector storage and citation highlights.
- [x] **AI Context Right-Click Menu & Inline Annotation Engine (Phase 3)**:
  - Native browser context menu registered in `background.js` with one-click actions (`explain`, `summarize`, `translate`, `grammar`).
  - Unit tests in `packages/zider/extension/test_context_menu.mjs`.
- [x] **Secure Extension CSP & Content Security Policy Hardening (Phase 4)**:
  - Enforced strict Manifest V3 CSP (`script-src 'self'`) without `unsafe-eval` in `manifest.json`.
  - Automated verification test in `packages/zider/scripts/verify_csp.test.mjs`.
- [x] **High-Precision Rerank & Web Grounding Pipeline (Phase 1)**:
  - Built `packages/zider/server/src/rerank_engine.mjs` with text overlap relevance scoring and minimum thresholding.
  - Unit tests in `packages/zider/server/test/rerank_engine.test.mjs`.
- [x] **Live YouTube Video & Audio Transcript Synchronizer (Phase 2)**:
  - Built `packages/zider/server/src/rerank_engine.mjs` providing `YouTubeSync` for playback timestamp alignment.
  - Unit tests in `packages/zider/server/test/rerank_engine.test.mjs`.

---

## 3. Active & Upcoming Implementation Workstreams

*(All Phases 1 through 4 for Zider Companion are now completed and verified).*

---

## 4. Verification & Validation Protocol

```bash
# 1. Zider Build & Test
pnpm --dir packages/zider test
pnpm --dir packages/zider build
```
