from __future__ import annotations
from dataclasses import dataclass, field
import json, time, urllib.error, urllib.request
@dataclass
class Usage:
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
@dataclass
class ProviderResult:
    content: str
    usage: Usage = field(default_factory=Usage)
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_message: dict = field(default_factory=dict)
class ProviderError(RuntimeError): pass
class MockProvider:
    def chat(self, model, messages, tools):
        latest = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        words = len(str(latest).split())
        content = f"[mock:{model}] Task completed. Received {words} words. Configure ZWORKFORCE_PROVIDER=openai-compatible for live model execution."
        return ProviderResult(content, Usage(max(1, words * 2), 0, max(1, len(content.split()) * 2)), [], {"role":"assistant","content":content})
class OpenAICompatibleProvider:
    def __init__(self, base_url, api_key, timeout=90, retries=3): self.base_url,self.api_key,self.timeout,self.retries=base_url.rstrip("/"),api_key,timeout,retries
    def chat(self, model, messages, tools):
        if not self.api_key: raise ProviderError("provider API key is missing")
        body={"model":model,"messages":messages,"temperature":0.2}
        if tools: body.update({"tools":tools,"tool_choice":"auto"})
        req=urllib.request.Request(self.base_url+"/chat/completions",data=json.dumps(body).encode(),headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json","User-Agent":"zWorkforce/1.0"},method="POST")
        last=None
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(req,timeout=self.timeout) as resp: data=json.loads(resp.read())
                msg=data["choices"][0]["message"]; u=data.get("usage",{}) or {}; pd=u.get("prompt_tokens_details",{}) or {}; calls=[]
                for call in msg.get("tool_calls",[]) or []:
                    fn=call.get("function",{})
                    try: args=json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError: args={"_raw":fn.get("arguments","")}
                    calls.append(ToolCall(call.get("id","tool"),fn.get("name",""),args))
                return ProviderResult(msg.get("content") or "",Usage(int(u.get("prompt_tokens",0)),int(pd.get("cached_tokens",0)),int(u.get("completion_tokens",0))),calls,msg)
            except urllib.error.HTTPError as exc:
                last=exc
                if exc.code not in {408,409,429,500,502,503,504}:
                    raise ProviderError(f"provider HTTP {exc.code}: {exc.read().decode(errors='replace')[:1000]}") from exc
            except (urllib.error.URLError,TimeoutError) as exc: last=exc
            time.sleep(min(2**attempt,8))
        raise ProviderError(f"provider request failed after {self.retries} attempts: {last}")
def build_provider(settings):
    if settings.provider=="mock": return MockProvider()
    if settings.provider=="openai-compatible": return OpenAICompatibleProvider(settings.provider_base_url,settings.provider_api_key)
    raise ValueError("ZWORKFORCE_PROVIDER must be mock or openai-compatible")
