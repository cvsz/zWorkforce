import base64
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional
try:
    from app.models import (
        ChatRequest,
        WriteRequest,
        TranslateRequest,
        BatchTranslateRequest,
        SummarizeRequest,
        PdfQueryRequest,
        AgentRunRequest,
        SearchRequest,
        VisionAnalyzeRequest,
        ImageGenRequest,
        ZWorkforceTaskRequest
    )
    from app.services.llm_gateway import LLMGateway
    from app.services.pdf_service import PDFService
    from app.services.summarizer_service import SummarizerService
    from app.services.translator_service import TranslatorService
    from app.services.agent_runner import AgentRunner
    from app.services.search_service import SearchService
    from app.services.vision_service import VisionService
    from app.services.prompt_library import PromptLibraryService
    from app.services.image_gen_service import ImageGenService
    from app.services.zworkforce_bridge import ZWorkforceBridge
except ImportError:
    from server.app.models import (
        ChatRequest,
        WriteRequest,
        TranslateRequest,
        BatchTranslateRequest,
        SummarizeRequest,
        PdfQueryRequest,
        AgentRunRequest,
        SearchRequest,
        VisionAnalyzeRequest,
        ImageGenRequest,
        ZWorkforceTaskRequest
    )
    from server.app.services.llm_gateway import LLMGateway
    from server.app.services.pdf_service import PDFService
    from server.app.services.summarizer_service import SummarizerService
    from server.app.services.translator_service import TranslatorService
    from server.app.services.agent_runner import AgentRunner
    from server.app.services.search_service import SearchService
    from server.app.services.vision_service import VisionService
    from server.app.services.prompt_library import PromptLibraryService
    from server.app.services.image_gen_service import ImageGenService
    from server.app.services.zworkforce_bridge import ZWorkforceBridge

router = APIRouter(prefix="/api")

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    messages_payload = [m.model_dump() for m in req.messages]
    
    # If web search is enabled, ground with search results
    if req.enable_web_search and req.messages:
        last_user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        if last_user_msg:
            search_res = await SearchService.search_web(last_user_msg, max_results=3)
            grounding_text = "\n".join([f"- [{r['title']}]({r['url']}): {r['snippet']}" for r in search_res.get("results", [])])
            messages_payload.insert(-1, {
                "role": "system",
                "content": f"[Web Search Grounding Results]:\n{grounding_text}"
            })

    return StreamingResponse(
        LLMGateway.stream_chat(
            model=req.model,
            messages=messages_payload,
            temperature=req.temperature,
            max_tokens=req.max_tokens
        ),
        media_type="text/event-stream"
    )

@router.post("/search")
async def search_endpoint(req: SearchRequest):
    return await SearchService.search_web(query=req.query, max_results=req.max_results)

@router.post("/vision/analyze")
async def vision_analyze(req: VisionAnalyzeRequest):
    return await VisionService.analyze_image(
        image_base64=req.image_base64,
        prompt=req.prompt,
        model=req.model
    )

@router.post("/image/generate")
async def image_generate(req: ImageGenRequest):
    return await ImageGenService.generate_image(
        prompt=req.prompt,
        size=req.size,
        style=req.style,
        model=req.model
    )

@router.get("/zworkforce/overview")
async def zworkforce_overview():
    return await ZWorkforceBridge.get_overview()

@router.post("/zworkforce/dispatch")
async def zworkforce_dispatch(req: ZWorkforceTaskRequest):
    return await ZWorkforceBridge.dispatch_task(
        title=req.title,
        prompt=req.prompt,
        target_agent=req.target_agent
    )

@router.get("/prompts")
async def get_prompts(category: Optional[str] = None):
    if category:
        return PromptLibraryService.get_by_category(category)
    return PromptLibraryService.get_all()

@router.post("/write")
async def write_assistant(req: WriteRequest):
    result = f"[{req.tone.upper()} {req.action.upper()}]\n\n{req.text}\n\n[Enhanced and polished draft]"
    return {"result": result, "action": req.action, "tone": req.tone}

@router.post("/translate")
async def translate_text(req: TranslateRequest):
    return await TranslatorService.translate(
        text=req.text,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        model=req.model
    )

@router.post("/translate/batch")
async def translate_batch(req: BatchTranslateRequest):
    translated_items = [
        f"[{req.target_lang.upper()}] {item}" for item in req.items
    ]
    return {
        "items": translated_items,
        "source_lang": req.source_lang,
        "target_lang": req.target_lang
    }

@router.post("/summarize/webpage")
async def summarize_webpage(req: SummarizeRequest):
    return await SummarizerService.summarize_webpage(
        url=req.url,
        raw_text=req.raw_text,
        model=req.model
    )

@router.post("/pdf/upload")
async def upload_pdf(request: Request):
    content_type = request.headers.get("content-type", "")
    filename = request.headers.get("x-filename", "uploaded.pdf")
    
    if "application/json" in content_type:
        body = await request.json()
        raw_b64 = body.get("file_base64", "")
        filename = body.get("filename", filename)
        content = base64.b64decode(raw_b64) if raw_b64 else b""
    else:
        content = await request.body()
    
    return await PDFService.process_pdf(content, filename)

@router.post("/pdf/query")
async def query_pdf(req: PdfQueryRequest):
    return await PDFService.query_doc(
        doc_id=req.doc_id,
        query=req.query,
        model=req.model
    )

@router.post("/agent/run")
async def run_agent(req: AgentRunRequest):
    return await AgentRunner.run_claw_task(
        goal=req.goal,
        model=req.model
    )
