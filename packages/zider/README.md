# zider — Enterprise AI Sidebar & Companion for zWorkforce (v1.2)

> Full-stack AI browser sidebar, ChatPDF, YouTube/Web summarizer, translator, code sandbox, voice input, image generator, and multi-model companion inspired by Sider.ai.

---

## 🌟 Full Feature Matrix

| Module | Core Features |
| :--- | :--- |
| **Persistent AI Sidebar** | Closed Shadow DOM overlay (`Ctrl+M` / `Cmd+M` toggle), edge toggle handle, responsive dark theme design system. |
| **Multi-Model & Group Chat** | Single chat or parallel comparison across **GPT-4o, Claude 3.5 Sonnet, Gemini 2.0, DeepSeek R1/V3, and Spawn Hermes 3 Free**. |
| **Voice Input & Read Aloud** | Web Speech API speech-to-text input (`🎙️`) + Text-to-Speech audio reader (`🔊 Read Aloud`). |
| **Web Search Grounding** | Real-time live web search citations integrated directly into conversational chat. |
| **Code & Artifacts Sandbox** | Interactive code editor, 1-click clipboard copy, and **Live HTML/SVG/Widget preview** directly inside the sidebar. |
| **Creative Studio (Draw)** | Text-to-Image AI generation with style presets (Photorealistic, Cyberpunk, Vector, 3D Render). |
| **In-Place Webpage Translation** | Quick selection popup translator + **In-place bilingual dual-column translation** across host webpage paragraphs. |
| **Distraction-Free Reader Mode** | 1-click reader mode stripping ads and navigation clutter with integrated AI Q&A. |
| **Inline Web Writing Assistant** | Floating "⚡ AI Write" button on inputs and textareas (Gmail, Twitter/X, LinkedIn, GitHub, Reddit) to compose, improve, or reply in-place. |
| **Vision & Screen OCR** | 1-click visible tab screen snipping, image upload, OCR text extraction, UI inspection, and visual Q&A. |
| **ChatPDF & Documents** | Multi-page PDF parsing, semantic chunking, and cited Q&A. |
| **Prompt Template Library** | Categorized prompt library covering Coding, Writing, Reading, Academic, and Web Automation. |
| **zWorkforce Control Plane Bridge** | Queue durable tasks and inspect worker status directly in the zWorkforce control plane (`:8000`). |
| **Chat History & Export** | Local session persistence across browser reloads + 1-click **Markdown export**. |
| **Extension Options Page** | Configure custom backend gateway URLs, default models, and keybindings via `options.html`. |

---

## 🚀 Quick Start

### 1. Start the zider Backend Gateway
```bash
cd packages/zider
make install
make dev
# Running on http://127.0.0.1:8085
```

### 2. Load the Chrome / Edge / Brave Extension
1. Navigate to `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked** and select [`packages/zider/extension`](file:///home/cvsz/zworkforce/packages/zider/extension)
4. Press `Ctrl+M` (or `Cmd+M`) on any website to toggle the AI Sidebar!

---

## 🧪 Testing

```bash
cd packages/zider
make test
# 11/11 tests passing: health, chat, search, vision, image gen, prompts, translate, summarize, sandbox, claw agent, and zworkforce bridge.
```
