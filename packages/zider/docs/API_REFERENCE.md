# zider API Reference (v1.1)

The zider Backend Gateway exposes high-throughput REST and Server-Sent Events (SSE) streaming endpoints on port `8085`.

---

## Complete Endpoints

### 1. Multi-Model Chat & Streaming
- `POST /api/chat/stream`
  - Body: `{"model": "gpt-4o", "messages": [...], "enable_web_search": true, "is_group": false}`
  - Response: Server-Sent Events (`text/event-stream`) with incremental token deltas.

### 2. Live Web Search & Grounding
- `POST /api/search`
  - Body: `{"query": "quantum computing breakthroughs 2026", "max_results": 5}`
  - Response: `{"query": "...", "results": [{"title": "...", "snippet": "...", "url": "..."}], "count": 5}`

### 3. Vision & Screenshot OCR
- `POST /api/vision/analyze`
  - Body: `{"image_base64": "data:image/png;base64,...", "prompt": "Extract text and UI hierarchy", "model": "..."}`
  - Response: `{"status": "success", "analysis": "...", "ocr_text": "..."}`

### 4. Categorized Prompt Library
- `GET /api/prompts?category=Coding`
  - Response: `[{"id": "...", "category": "Coding", "title": "...", "icon": "...", "template": "..."}]`

### 5. Document & ChatPDF
- `POST /api/pdf/upload` (Supports base64 JSON payload and raw stream)
  - Response: `{"doc_id": "doc_...", "filename": "report.pdf", "num_pages": 12, "num_chunks": 36}`
- `POST /api/pdf/query`
  - Body: `{"doc_id": "doc_...", "query": "What was the revenue growth?", "model": "..."}`

### 6. Writing Studio & Inline DOM Helper
- `POST /api/write`
  - Body: `{"action": "improve|compose|grammar|reply|expand", "text": "...", "tone": "professional"}`

### 7. Translation (Single & Batch)
- `POST /api/translate`
  - Body: `{"text": "...", "source_lang": "auto", "target_lang": "es"}`
- `POST /api/translate/batch`
  - Body: `{"items": ["Title", "Paragraph"], "source_lang": "en", "target_lang": "es"}`

### 8. Web & Media Summarization
- `POST /api/summarize/webpage`
  - Body: `{"url": "https://example.com/blog", "raw_text": "...", "model": "..."}`
- `POST /api/summarize/youtube`
  - Body: `{"video_url": "https://youtube.com/watch?v=..."}`

### 9. Autonomous Browser Agent
- `POST /api/agent/run`
  - Body: `{"goal": "Extract table items from current page", "model": "..."}`
