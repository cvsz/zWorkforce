# Sider.ai vs. zider: Architectural Comparison

| Dimension | Sider.ai (Proprietary SaaS) | zider (zWorkforce Open Platform) |
| :--- | :--- | :--- |
| **Licensing** | Proprietary Commercial SaaS / Closed-source | Open Source (MIT) under zWorkforce ecosystem |
| **Data Privacy & Storage** | Proprietary cloud servers / Third-party storage | Self-hosted or Tenant-isolated within zWorkforce control plane |
| **Model Freedom** | Fixed subscription tiers / Token credits | Bring-Your-Own-Key (OpenAI, Anthropic, Gemini, DeepSeek) + 100% Free OpenRouter / Hermes models |
| **Sidebar Architecture** | Extension iframe / Web components | Closed Shadow DOM isolation + Manifest V3 service worker |
| **Group AI Chat** | Supported | Fully supported with SSE parallel streaming comparison |
| **ChatPDF & Documents** | Server-side upload to proprietary cloud | Local / Self-hosted vector RAG or zWorkforce vector backend |
| **Autonomous Browser Agents** | Claw Agent (Cloud driven) | Claw & Code agents with local sandbox and explicit human-in-the-loop gates |
| **Extensibility** | Closed platform | Custom plugins, custom prompt libraries, integration with zWorkforce workers |
