# Security Policy — zider

## Security Directives
1. **Server-Side API Credentials**: Never package API keys (OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter) inside the client-side extension or frontend assets. All authorization is handled server-side at the zider BFF / zWorkforce control plane.
2. **DOM Isolation**: The content script uses Closed Shadow DOM (`mode: 'closed'`) to inject the sidebar and selection popup. No script tags or external resources are evaluated dynamically via `eval()` or inline execution.
3. **SSRF Defenses**: Server-side URL fetching (for YouTube and webpage summarization) validates IP ranges and forbids fetching RFC1918 private loopback/internal addresses unless explicitly whitelisted in local dev.
4. **Agent Action Guardrails**: The Claw / Code browser agent can only trigger mutating actions (DOM input, button clicks, downloads) after explicit approval through user prompts.
