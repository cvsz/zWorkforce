import json
import asyncio
from typing import AsyncGenerator, List, Dict, Any
import httpx
from server.app.config import settings

class LLMGateway:
    """
    Multi-model streaming gateway supporting OpenAI, Anthropic, Gemini, DeepSeek,
    and fallback to OpenRouter / Spawn Hermes Free.
    """

    @classmethod
    async def stream_chat(
        cls,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        # Handle OpenRouter / Hermes free or custom providers
        api_key = settings.openrouter_api_key or settings.openai_api_key
        headers = {
            "Authorization": f"Bearer {api_key}" if api_key else "Bearer anonymous",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/cvsz/zworkforce",
            "X-Title": "zider AI Companion"
        }

        # Resolve OpenRouter model ID
        model_aliases = {
            "openrouter/spawn-hermes-free": "nousresearch/hermes-3-llama-3.1-405b:free",
            "deepseek/deepseek-r1:free": "deepseek/deepseek-r1:free",
            "meta-llama/llama-3.3-70b-instruct:free": "meta-llama/llama-3.3-70b-instruct:free",
            "qwen/qwen-2.5-coder-32b-instruct:free": "qwen/qwen-2.5-coder-32b-instruct:free",
            "anthropic/claude-3-7-sonnet": "anthropic/claude-3.7-sonnet",
            "anthropic/claude-3-5-sonnet": "anthropic/claude-3.5-sonnet",
            "openai/o3-mini": "openai/o3-mini",
            "openai/gpt-4o": "openai/gpt-4o",
            "google/gemini-2.0-flash": "google/gemini-2.0-flash-001",
            "deepseek/deepseek-r1": "deepseek/deepseek-r1",
            "x-ai/grok-2": "x-ai/grok-2"
        }
        resolved_model = model_aliases.get(model, model)

        payload = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        # If live API key is configured, stream from OpenRouter / upstream
        if api_key:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload
                    ) as response:
                        if response.status_code != 200:
                            yield f"data: {json.dumps({'delta': f'Upstream error: HTTP {response.status_code}'})}\n\n"
                            yield "data: [DONE]\n\n"
                            return

                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data_content = line[6:].strip()
                                if data_content == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                    break
                                try:
                                    chunk = json.loads(data_content)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta:
                                        yield f"data: {json.dumps({'delta': delta})}\n\n"
                                except Exception:
                                    pass
                return
            except Exception as e:
                # Fallback to local response mock if offline
                pass

        # Offline / Local fallback simulation for instant responsiveness
        sample_response = (
            f"[zider Response via {model}]\n\n"
            f"I have received your query with {len(messages)} messages in context. "
            "To enable live multi-model streaming with Claude, GPT-4o, Gemini, or DeepSeek, "
            "ensure `OPENROUTER_API_KEY` or respective provider keys are exported."
        )
        for word in sample_response.split(" "):
            yield f"data: {json.dumps({'delta': word + ' '})}\n\n"
            await asyncio.sleep(0.04)
        yield "data: [DONE]\n\n"
