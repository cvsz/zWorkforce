from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "openrouter/spawn-hermes-free"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 2048
    is_group: bool = False
    enable_web_search: bool = False


class WriteRequest(BaseModel):
    action: str = Field(..., description="compose | improve | grammar | reply | expand")
    text: str
    tone: str = "professional"
    model: str = "openrouter/spawn-hermes-free"


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "auto"
    target_lang: str = "en"
    model: str = "openrouter/spawn-hermes-free"


class BatchTranslateRequest(BaseModel):
    items: List[str]
    source_lang: str = "auto"
    target_lang: str = "en"
    model: str = "openrouter/spawn-hermes-free"


class SummarizeRequest(BaseModel):
    url: Optional[str] = None
    raw_text: Optional[str] = None
    mode: str = "executive"
    model: str = "openrouter/spawn-hermes-free"


class PdfQueryRequest(BaseModel):
    doc_id: str
    query: str
    model: str = "openrouter/spawn-hermes-free"


class BrowserActionRequest(BaseModel):
    kind: str = Field(..., description="navigate | inspect | screenshot | extract | click | submit | upload")
    url: str
    selector: str = ""
    value: str = ""
    artifact_id: str = ""
    idempotency_key: str = ""


class AgentRunRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=4000)
    model: str = "openrouter/spawn-hermes-free"
    actions: List[BrowserActionRequest] = Field(default_factory=list, max_length=20)
    approval_token: str = Field(default="", max_length=2048)


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


class VisionAnalyzeRequest(BaseModel):
    image_base64: str
    prompt: Optional[str] = None
    model: str = "openrouter/spawn-hermes-free"


class ImageGenRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    style: str = "photorealistic"
    model: str = "openrouter/spawn-hermes-free"


class ZWorkforceTaskRequest(BaseModel):
    title: str
    prompt: str
    target_agent: str = "general"
