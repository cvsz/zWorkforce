# Provider List

This file records the approved AI provider surfaces and model catalog entries for Z Platform. It is a configuration and operations reference, not a secret store.

## Rules

- Provider credentials must stay server-side in the AI Gateway runtime.
- Browser clients must use platform model IDs and must never receive upstream provider keys.
- A provider entry does not grant hosted inference by itself. Operators must provision the local runtime, self-hosted service, or upstream endpoint.
- Financial, wallet, payment-card, Cloudflare, and infrastructure credentials are outside the AI request path.

## Runtime Provider Surfaces

| Provider surface | `UPSTREAM_PROVIDER` | Endpoint shape | Credential env | Status | Notes |
|---|---|---|---|---|---|
| OpenAI-compatible | `openai-compatible` | `/v1/chat/completions`, `/v1/files` | `UPSTREAM_API_KEY` | active | Default adapter for LiteLLM, OpenAI-compatible local servers, vLLM OpenAI server, TGI OpenAI-compatible fronts, Ollama-compatible proxies, and compatible cloud gateways. Supports binary/content upload pass-through with safe filename normalization. |
| OpenAI-compatible alias | `openai` | `/v1/chat/completions`, `/v1/files` | `UPSTREAM_API_KEY` | active | Same message and upload shape as `openai-compatible`; useful when the operator wants a shorter provider label. |
| Anthropic message shape | `anthropic` | chat/messages-compatible upstream behind gateway normalization | `UPSTREAM_API_KEY` | partial | Attachment references are translated into appended user content blocks. Binary file uploads return `unsupported_upload_provider` until an approved Anthropic content upload contract is added. |
| Hugging Face catalog | `openai-compatible` | metadata via `GET /v1/models`; inference through configured compatible runtime | `UPSTREAM_API_KEY` when using a hosted endpoint | partial | Catalog is bundled metadata for free/local/open-license model candidates. Runtime must be local, self-hosted, or operator-provisioned. |

## Required Environment

| Variable | Required | Purpose |
|---|---:|---|
| `Z_PLATFORM_SERVICE_TOKEN` | yes | Internal bearer token accepted from trusted platform clients. |
| `UPSTREAM_BASE_URL` | yes for inference | Approved upstream base URL. Both `http://provider` and `http://provider/v1` are accepted. |
| `UPSTREAM_API_KEY` | yes for inference | Upstream credential held only by the gateway. For local runtimes, use a local service token or placeholder only when the runtime requires one. |
| `UPSTREAM_PROVIDER` | no | Attachment/message-shape and upload adapter. Defaults to `openai-compatible`. |

## Hugging Face Free/Local Catalog

These entries are exposed through `GET /v1/models` with `Authorization: Bearer <Z_PLATFORM_SERVICE_TOKEN>`. They use the `hf:` prefix so clients can distinguish platform catalog IDs from raw upstream model IDs.

| Platform model ID | Hugging Face repo | License | Profile | Runtime candidates | Notes |
|---|---|---|---|---|---|
| `hf:Qwen/Qwen3-0.6B` | `Qwen/Qwen3-0.6B` | Apache-2.0 | small-chat | HF endpoint, local Transformers, TGI | Small open-weight Qwen3 chat/text-generation model for low-cost testing. |
| `hf:Qwen/Qwen3-4B` | `Qwen/Qwen3-4B` | Apache-2.0 | balanced-chat | HF endpoint, local Transformers, TGI | Balanced Qwen3 option for chat and coding-adjacent tasks. |
| `hf:Qwen/Qwen3-8B` | `Qwen/Qwen3-8B` | Apache-2.0 | general-chat | HF endpoint, local Transformers, TGI | Popular Qwen3 general text-generation model. |
| `hf:Qwen/Qwen2.5-1.5B-Instruct` | `Qwen/Qwen2.5-1.5B-Instruct` | Apache-2.0 | small-instruct | HF endpoint, local Transformers, TGI | Small instruct model for fast local tests. |
| `hf:Qwen/Qwen2.5-7B-Instruct` | `Qwen/Qwen2.5-7B-Instruct` | Apache-2.0 | general-instruct | HF endpoint, local Transformers, TGI | Strong open instruct baseline with broad runtime support. |
| `hf:openai/gpt-oss-20b` | `openai/gpt-oss-20b` | Apache-2.0 | large-reasoning | HF endpoint, vLLM, TGI | Higher-quality reasoning candidate when sufficient GPU is available. |
| `hf:deepseek-ai/DeepSeek-R1` | `deepseek-ai/DeepSeek-R1` | MIT | large-reasoning | HF endpoint, vLLM, TGI | Open reasoning model; practical use usually needs hosted or GPU runtime. |
| `hf:microsoft/Phi-3-small-8k-instruct` | `microsoft/Phi-3-small-8k-instruct` | MIT | small-instruct | HF endpoint, local Transformers | Small instruct model with code and multilingual tags. |
| `hf:microsoft/Phi-3-small-128k-instruct` | `microsoft/Phi-3-small-128k-instruct` | MIT | long-context-instruct | HF endpoint, local Transformers | Long-context small instruct candidate. |
| `hf:Tiiny/SmallThinker-4BA0.6B-Instruct` | `Tiiny/SmallThinker-4BA0.6B-Instruct` | Apache-2.0 | tiny-reasoning | HF endpoint, local Transformers | Tiny reasoning/instruct model for smoke tests and constrained devices. |
| `hf:SmallDoge/Doge-160M-Instruct` | `SmallDoge/Doge-160M-Instruct` | Apache-2.0 | tiny-qa | HF endpoint, local Transformers | Tiny QA/instruct model for health checks and very low-resource tests. |
| `hf:unsloth/Mistral-Small-24B-Instruct-2501-GGUF` | `unsloth/Mistral-Small-24B-Instruct-2501-GGUF` | Apache-2.0 | local-gguf-instruct | local GGUF, llama.cpp, Ollama-compatible | Local GGUF candidate for llama.cpp/Ollama-style serving. |
| `hf:unsloth/Mistral-Small-24B-Instruct-2501-unsloth-bnb-4bit` | `unsloth/Mistral-Small-24B-Instruct-2501-unsloth-bnb-4bit` | Apache-2.0 | quantized-instruct | HF endpoint, local Transformers, bitsandbytes | 4-bit quantized Mistral Small instruct variant. |
| `hf:byteshape/Devstral-Small-2-24B-Instruct-2512-GGUF` | `byteshape/Devstral-Small-2-24B-Instruct-2512-GGUF` | Apache-2.0 | local-gguf-coding | local GGUF, llama.cpp, Ollama-compatible | Coding-oriented local GGUF candidate. |

## Local Runtime Examples

| Runtime | Provider setting | Expected gateway base URL |
|---|---|---|
| LiteLLM proxy | `UPSTREAM_PROVIDER=openai-compatible` | `UPSTREAM_BASE_URL=http://litellm:4000/v1` |
| vLLM OpenAI server | `UPSTREAM_PROVIDER=openai-compatible` | `UPSTREAM_BASE_URL=http://vllm:8000/v1` |
| Text Generation Inference with compatible front | `UPSTREAM_PROVIDER=openai-compatible` | `UPSTREAM_BASE_URL=http://tgi-gateway:8080/v1` |
| Ollama-compatible proxy | `UPSTREAM_PROVIDER=openai-compatible` | `UPSTREAM_BASE_URL=http://ollama-proxy:11434/v1` |
| Anthropic-compatible gateway | `UPSTREAM_PROVIDER=anthropic` | `UPSTREAM_BASE_URL=http://anthropic-gateway:8400/v1` |

## Follow-Up Work

- Add approved binary/content upload contracts for non-OpenAI-compatible upstreams.
- Add operator-managed model availability checks.
- Add tenant-scoped model entitlement policy.
- Add usage events per provider and model.
- Verify GitHub Actions for the AI Gateway test suite.
