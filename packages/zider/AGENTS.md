# AGENTS.md — zider Control Plane & Agent Guidelines

## Intent
`zider` is an open-source, full-stack, enterprise-grade AI Sidebar and Browser Workspace companion for zWorkforce, inspired by Sider.ai. It brings persistent multi-model chat (GPT-4o, Claude 3.5, Gemini 2.0/3.0, DeepSeek R1/V3, Grok, OpenRouter/Hermes), ChatPDF document intelligence, YouTube & Webpage summarization, live side-by-side translation, AI writing assistant, and autonomous browser workflow agents into a zero-latency sidebar.

## Core Directives
1. **Tenant Isolation & Server-Side Secrets**: Browser extension clients and static frontend assets must NEVER receive raw API provider keys directly. All LLM calls, document embeddings, and model requests proxy through the zider BFF / zWorkforce control plane.
2. **Manifest V3 Strict Compliance**: Use background service workers, declarativeNetRequest / bounded fetch, isolated content scripts, and secure Shadow DOM injection for sidebar isolation without polluting host web pages.
3. **Multi-Model Orchestration**: Support single chat, group AI chat (parallel multi-model compare), streaming SSE, and zero-cost OpenRouter/Hermes Free fallback.
4. **Tool Guardrails & Bounded Actions**: Autonomous web agents (Claw/Code runners) require explicit user authorization for state-mutating actions (clicks, form submits, file uploads).
