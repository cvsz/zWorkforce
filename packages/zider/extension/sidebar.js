/**
 * zider Sidebar Reactive Logic & Streaming Client (v1.2)
 */

const API_BASE = "http://127.0.0.1:8085";

// Navigation & Model Elements
const navTabs = document.querySelectorAll(".nav-tab");
const tabPanes = document.querySelectorAll(".tab-pane");
const modelSelect = document.getElementById("model-select");

// Chat Elements
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatSendBtn = document.getElementById("chat-send-btn");
const clearChatBtn = document.getElementById("clear-chat-btn");
const exportChatBtn = document.getElementById("export-chat-btn");
const ttsLatestBtn = document.getElementById("tts-latest-btn");
const voiceInputBtn = document.getElementById("voice-input-btn");
const groupChatToggle = document.getElementById("group-chat-toggle");
const webSearchToggle = document.getElementById("web-search-toggle");

// Vision Elements
const snipScreenBtn = document.getElementById("snip-screen-btn");
const uploadImgBtn = document.getElementById("upload-img-btn");
const visionFileInput = document.getElementById("vision-file-input");
const visionPreviewContainer = document.getElementById("vision-preview-container");
const visionPreviewImg = document.getElementById("vision-preview-img");
const clearVisionBtn = document.getElementById("clear-vision-btn");
const visionPromptInput = document.getElementById("vision-prompt-input");
const visionRunBtn = document.getElementById("vision-run-btn");
const visionResult = document.getElementById("vision-result");
let currentVisionBase64 = null;

// Draw Elements
const drawPromptInput = document.getElementById("draw-prompt-input");
const drawGenerateBtn = document.getElementById("draw-generate-btn");
const drawOutput = document.getElementById("draw-output");
let activeDrawStyle = "photorealistic";

// Write Elements
const writeTaskSelect = document.getElementById("write-task-select");
const writeInput = document.getElementById("write-input");
const writeGenerateBtn = document.getElementById("write-generate-btn");
const writeInsertBtn = document.getElementById("write-insert-btn");
const writeResult = document.getElementById("write-result");
let activeTone = "professional";

// Read Elements
const readSummarizePageBtn = document.getElementById("read-summarize-page-btn");
const readSummarizeYtBtn = document.getElementById("read-summarize-yt-btn");
const readDistractionFreeBtn = document.getElementById("read-distraction-free-btn");
const readSummaryOutput = document.getElementById("read-summary-output");

// PDF Elements
const pdfDropzone = document.getElementById("pdf-upload-dropzone");
const pdfFileInput = document.getElementById("pdf-file-input");
const pdfActiveDoc = document.getElementById("pdf-active-doc");
const pdfDocName = document.getElementById("pdf-doc-name");
const pdfRemoveBtn = document.getElementById("pdf-remove-btn");
const pdfMessages = document.getElementById("pdf-messages");
const pdfQueryInput = document.getElementById("pdf-query-input");
const pdfSendBtn = document.getElementById("pdf-send-btn");
let currentDocId = null;

// Translate Elements
const transSource = document.getElementById("trans-source");
const transTarget = document.getElementById("trans-target");
const transInput = document.getElementById("trans-input");
const transBtn = document.getElementById("trans-btn");
const transPageBtn = document.getElementById("trans-page-btn");
const transOutput = document.getElementById("trans-output");

// Sandbox Elements
const sandboxCodeInput = document.getElementById("sandbox-code-input");
const sandboxRunHtmlBtn = document.getElementById("sandbox-run-html-btn");
const sandboxCopyCodeBtn = document.getElementById("sandbox-copy-code-btn");
const sandboxFrame = document.getElementById("sandbox-frame");

// Agent & zWorkforce Elements
const agentGoalInput = document.getElementById("agent-goal-input");
const agentRunBtn = document.getElementById("agent-run-btn");
const agentDispatchZwfBtn = document.getElementById("agent-dispatch-zwf-btn");
const agentLogs = document.getElementById("agent-logs");

// Prompt Library Elements
const promptLibBtn = document.getElementById("prompt-lib-btn");
const promptModal = document.getElementById("prompt-modal");
const closePromptModal = document.getElementById("close-prompt-modal");
const promptList = document.getElementById("prompt-list");
const pChips = document.querySelectorAll(".p-chip");

// --- Tab Switching ---
navTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    navTabs.forEach((t) => t.classList.remove("active"));
    tabPanes.forEach((p) => p.classList.remove("active"));

    tab.classList.add("active");
    const target = tab.getAttribute("data-target");
    const pane = document.getElementById(target);
    if (pane) pane.classList.add("active");
  });
});

function switchTab(tabId) {
  navTabs.forEach((t) => {
    if (t.getAttribute("data-target") === tabId) t.classList.add("active");
    else t.classList.remove("active");
  });
  tabPanes.forEach((p) => {
    if (p.id === tabId) p.classList.add("active");
    else p.classList.remove("active");
  });
}

// --- Style & Tone Chips ---
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", (e) => {
    const parent = chip.parentElement;
    parent.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    if (chip.hasAttribute("data-tone")) activeTone = chip.getAttribute("data-tone");
    if (chip.hasAttribute("data-style")) activeDrawStyle = chip.getAttribute("data-style");
  });
});

// --- Chat Handling & History ---
let chatHistory = [];
try {
  const saved = localStorage.getItem("zider_chat_history");
  if (saved) chatHistory = JSON.parse(saved);
} catch (e) {}

function saveChatHistory() {
  try {
    localStorage.setItem("zider_chat_history", JSON.stringify(chatHistory));
  } catch (e) {}
}

function appendMessage(role, text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${role}`;
  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = role === "user" ? "👤" : "⚡";
  
  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.textContent = text;

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return bubble;
}

if (chatHistory.length > 0) {
  chatHistory.forEach((msg) => {
    appendMessage(msg.role, msg.content);
  });
}

async function sendChatMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  appendMessage("user", text);
  chatHistory.push({ role: "user", content: text });
  saveChatHistory();
  chatInput.value = "";

  const isGroup = groupChatToggle.checked;
  const isWebSearch = webSearchToggle.checked;
  const selectedModel = modelSelect.value;
  const assistantBubble = appendMessage("assistant", isWebSearch ? "Searching & Thinking..." : "Thinking...");

  try {
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: selectedModel,
        messages: chatHistory,
        is_group: isGroup,
        enable_web_search: isWebSearch
      })
    });

    if (!res.ok) {
      assistantBubble.textContent = `Error: ${res.statusText}. Please verify zider BFF is running on port 8085.`;
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    assistantBubble.textContent = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const dataStr = line.replace("data: ", "").trim();
          if (dataStr === "[DONE]") break;
          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.delta) {
              assistantBubble.textContent += parsed.delta;
              chatMessages.scrollTop = chatMessages.scrollHeight;
            }
          } catch (e) {
            assistantBubble.textContent += dataStr;
          }
        }
      }
    }
    chatHistory.push({ role: "assistant", content: assistantBubble.textContent });
    saveChatHistory();
  } catch (err) {
    assistantBubble.textContent = `Connection failed: ${err.message}. Backend running at ${API_BASE}?`;
  }
}

chatSendBtn.addEventListener("click", sendChatMessage);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendChatMessage();
  }
});

// Voice Input Web Speech API
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRec();
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onstart = () => voiceInputBtn.classList.add("recording");
  recognition.onend = () => voiceInputBtn.classList.remove("recording");
  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    chatInput.value += (chatInput.value ? " " : "") + transcript;
    chatInput.focus();
  };

  voiceInputBtn.addEventListener("click", () => {
    try { recognition.start(); } catch (e) { recognition.stop(); }
  });
} else {
  voiceInputBtn.style.display = "none";
}

// Text-to-Speech Read Aloud
ttsLatestBtn.addEventListener("click", () => {
  const lastAssistantMsg = [...chatHistory].reverse().find(m => m.role === "assistant");
  if (lastAssistantMsg && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(lastAssistantMsg.content);
    window.speechSynthesis.speak(utterance);
  }
});

clearChatBtn.addEventListener("click", () => {
  chatHistory = [];
  saveChatHistory();
  chatMessages.innerHTML = `
    <div class="message assistant">
      <div class="msg-avatar">⚡</div>
      <div class="msg-bubble">Conversation cleared! What can I help you with?</div>
    </div>
  `;
});

exportChatBtn.addEventListener("click", () => {
  if (chatHistory.length === 0) return;
  const mdContent = chatHistory.map((m) => `### ${m.role === "user" ? "User" : "zider AI"}\n${m.content}\n`).join("\n---\n\n");
  const blob = new Blob([mdContent], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `zider-chat-export-${Date.now()}.md`;
  a.click();
});

// --- Creative Studio Draw ---
drawGenerateBtn.addEventListener("click", async () => {
  const prompt = drawPromptInput.value.trim();
  if (!prompt) return;
  drawOutput.innerHTML = "<p style='color:#a1a1aa;'>Synthesizing visual artwork...</p>";

  try {
    const res = await fetch(`${API_BASE}/api/image/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: prompt,
        style: activeDrawStyle,
        model: modelSelect.value
      })
    });
    const data = await res.json();
    drawOutput.innerHTML = `
      <img src="${data.image_url}" style="max-width:100%;border-radius:8px;box-shadow:0 4px 15px rgba(0,0,0,0.5);">
      <p style="font-size:11px;color:#a1a1aa;margin-top:6px;">Style: ${data.style} | Generated via zider AI</p>
    `;
  } catch (err) {
    drawOutput.innerHTML = `<p style="color:#ef4444;">Generation error: ${err.message}</p>`;
  }
});

// --- Live Sandbox & Code Preview ---
function updateSandboxPreview() {
  const code = sandboxCodeInput.value;
  const doc = sandboxFrame.contentDocument || sandboxFrame.contentWindow.document;
  doc.open();
  doc.write(code);
  doc.close();
}
sandboxRunHtmlBtn.addEventListener("click", updateSandboxPreview);
sandboxCopyCodeBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(sandboxCodeInput.value);
  sandboxCopyCodeBtn.textContent = "✔ Copied!";
  setTimeout(() => { sandboxCopyCodeBtn.textContent = "📋 Copy Code"; }, 2000);
});
updateSandboxPreview();

// --- Vision / OCR Handling ---
snipScreenBtn.addEventListener("click", () => {
  window.parent.postMessage({ type: "ZIDER_CAPTURE_SNIP_REQUEST" }, "*");
});

uploadImgBtn.addEventListener("click", () => visionFileInput.click());
visionFileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => setVisionImage(reader.result);
  reader.readAsDataURL(file);
});

function setVisionImage(dataUrl) {
  currentVisionBase64 = dataUrl;
  visionPreviewImg.src = dataUrl;
  visionPreviewContainer.style.display = "flex";
  visionRunBtn.disabled = false;
  switchTab("tab-vision");
}

clearVisionBtn.addEventListener("click", () => {
  currentVisionBase64 = null;
  visionPreviewImg.src = "";
  visionPreviewContainer.style.display = "none";
  visionRunBtn.disabled = true;
  visionResult.textContent = "";
});

visionRunBtn.addEventListener("click", async () => {
  if (!currentVisionBase64) return;
  visionResult.textContent = "Analyzing image with Vision & OCR AI...";
  try {
    const res = await fetch(`${API_BASE}/api/vision/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_base64: currentVisionBase64,
        prompt: visionPromptInput.value,
        model: modelSelect.value
      })
    });
    const data = await res.json();
    visionResult.textContent = data.analysis || "Analysis completed.";
  } catch (err) {
    visionResult.textContent = `Error: ${err.message}`;
  }
});

// --- Reader Mode & Page Translate Triggers ---
readDistractionFreeBtn.addEventListener("click", () => {
  window.parent.postMessage({ type: "ZIDER_TRIGGER_READER_MODE" }, "*");
});
transPageBtn.addEventListener("click", () => {
  window.parent.postMessage({ type: "ZIDER_TRIGGER_PAGE_TRANSLATE", targetLang: transTarget.value }, "*");
});

// --- Write Assistant ---
async function runWrite() {
  const text = writeInput.value.trim();
  if (!text) return;
  writeResult.textContent = "Drafting with AI...";

  try {
    const res = await fetch(`${API_BASE}/api/write`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: writeTaskSelect.value,
        text: text,
        tone: activeTone,
        model: modelSelect.value
      })
    });
    const data = await res.json();
    writeResult.textContent = data.result || "No response received.";
    writeInsertBtn.style.display = "inline-block";
  } catch (e) {
    writeResult.textContent = `Error: ${e.message}`;
  }
}
writeGenerateBtn.addEventListener("click", runWrite);
writeInsertBtn.addEventListener("click", () => {
  const text = writeResult.textContent;
  window.parent.postMessage({ type: "ZIDER_INSERT_TEXT_TO_INPUT", text: text }, "*");
});

// --- Translation ---
async function runTranslation() {
  const text = transInput.value.trim();
  if (!text) return;
  transOutput.textContent = "Translating...";

  try {
    const res = await fetch(`${API_BASE}/api/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        source_lang: transSource.value,
        target_lang: transTarget.value,
        model: modelSelect.value
      })
    });
    const data = await res.json();
    transOutput.textContent = data.translated_text || "Translation completed.";
  } catch (e) {
    transOutput.textContent = `Error: ${e.message}`;
  }
}
transBtn.addEventListener("click", runTranslation);

// --- Summarizer ---
async function summarizeText(text) {
  try {
    const res = await fetch(`${API_BASE}/api/summarize/webpage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: text, model: modelSelect.value })
    });
    const data = await res.json();
    readSummaryOutput.textContent = data.summary || "Summary completed.";
  } catch (e) {
    readSummaryOutput.textContent = `Error: ${e.message}`;
  }
}

async function summarizeActivePage(url) {
  readSummaryOutput.textContent = "Extracting and summarizing webpage...";
  try {
    const res = await fetch(`${API_BASE}/api/summarize/webpage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url, model: modelSelect.value })
    });
    const data = await res.json();
    readSummaryOutput.textContent = data.summary || "Summary generated.";
  } catch (e) {
    readSummaryOutput.textContent = `Error: ${e.message}`;
  }
}

readSummarizePageBtn.addEventListener("click", () => {
  window.parent.postMessage({ type: "ZIDER_REQUEST_ACTIVE_URL" }, "*");
  readSummaryOutput.textContent = "Fetching current webpage context...";
});

// --- PDF Upload & Query ---
pdfDropzone.addEventListener("click", () => pdfFileInput.click());
pdfFileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async () => {
    const b64 = reader.result.split(",")[1];
    pdfDropzone.style.display = "none";
    pdfActiveDoc.style.display = "flex";
    pdfDocName.textContent = file.name;

    try {
      const res = await fetch(`${API_BASE}/api/pdf/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          file_base64: b64
        })
      });
      const data = await res.json();
      currentDocId = data.doc_id;
      pdfQueryInput.disabled = false;
      pdfSendBtn.disabled = false;
      pdfQueryInput.focus();
    } catch (err) {
      alert("Failed to upload PDF: " + err.message);
    }
  };
  reader.readAsDataURL(file);
});

pdfRemoveBtn.addEventListener("click", () => {
  currentDocId = null;
  pdfActiveDoc.style.display = "none";
  pdfDropzone.style.display = "block";
  pdfQueryInput.disabled = true;
  pdfSendBtn.disabled = true;
  pdfMessages.innerHTML = "";
});

pdfSendBtn.addEventListener("click", async () => {
  const query = pdfQueryInput.value.trim();
  if (!query || !currentDocId) return;

  const qDiv = document.createElement("div");
  qDiv.className = "message user";
  qDiv.innerHTML = `<div class="msg-bubble">${query}</div>`;
  pdfMessages.appendChild(qDiv);
  pdfQueryInput.value = "";

  try {
    const res = await fetch(`${API_BASE}/api/pdf/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        doc_id: currentDocId,
        query: query,
        model: modelSelect.value
      })
    });
    const data = await res.json();
    const aDiv = document.createElement("div");
    aDiv.className = "message assistant";
    aDiv.innerHTML = `<div class="msg-bubble">${data.answer}</div>`;
    pdfMessages.appendChild(aDiv);
  } catch (err) {
    const errDiv = document.createElement("div");
    errDiv.className = "message assistant";
    errDiv.innerHTML = `<div class="msg-bubble">Error: ${err.message}</div>`;
    pdfMessages.appendChild(errDiv);
  }
});

// --- Agent Claw & zWorkforce Task Dispatch ---
agentRunBtn.addEventListener("click", async () => {
  const goal = agentGoalInput.value.trim();
  if (!goal) return;

  agentLogs.textContent = "⚡ Agent Initializing...\n[1/3] Decomposing workflow into browser steps...\n";
  try {
    const res = await fetch(`${API_BASE}/api/agent/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal: goal, model: modelSelect.value })
    });
    const data = await res.json();
    agentLogs.textContent += `[2/3] Executing planned actions...\n${data.steps.join("\n")}\n\n[3/3] Task Complete: ${data.result}`;
  } catch (err) {
    agentLogs.textContent += `\n❌ Execution halted: ${err.message}`;
  }
});

agentDispatchZwfBtn.addEventListener("click", async () => {
  const goal = agentGoalInput.value.trim();
  if (!goal) return;

  agentLogs.textContent = "🚀 Dispatching durable task to zWorkforce Control Plane (:8000)...\n";
  try {
    const res = await fetch(`${API_BASE}/api/zworkforce/dispatch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "zider Browser Task",
        prompt: goal,
        target_agent: "general"
      })
    });
    const data = await res.json();
    agentLogs.textContent += `✔ Task Queued: ${data.task_id || "OK"}\nStatus: ${data.status}\nMessage: ${data.message || "Enqueued"}`;
  } catch (err) {
    agentLogs.textContent += `❌ Dispatch failed: ${err.message}`;
  }
});

// --- Prompt Library Modal ---
promptLibBtn.addEventListener("click", async () => {
  promptModal.style.display = "flex";
  loadPrompts("all");
});

closePromptModal.addEventListener("click", () => {
  promptModal.style.display = "none";
});

pChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    pChips.forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    loadPrompts(chip.getAttribute("data-pcat"));
  });
});

async function loadPrompts(cat) {
  promptList.innerHTML = "Loading prompts...";
  try {
    const url = cat === "all" ? `${API_BASE}/api/prompts` : `${API_BASE}/api/prompts?category=${cat}`;
    const res = await fetch(url);
    const prompts = await res.json();
    promptList.innerHTML = "";
    prompts.forEach((p) => {
      const card = document.createElement("div");
      card.className = "prompt-card";
      card.innerHTML = `
        <div class="prompt-title">${p.icon} ${p.title}</div>
        <div class="prompt-preview">${p.template.slice(0, 75)}...</div>
      `;
      card.addEventListener("click", () => {
        promptModal.style.display = "none";
        switchTab("tab-chat");
        chatInput.value = p.template;
        chatInput.focus();
      });
      promptList.appendChild(card);
    });
  } catch (e) {
    promptList.innerHTML = `Error loading prompts: ${e.message}`;
  }
}

// --- Quick Action Handlers from Content Script ---
window.addEventListener("message", (event) => {
  const data = event.data;
  if (!data) return;

  if (data.type === "ZIDER_SCREENSHOT_IMAGE") {
    setVisionImage(data.dataUrl);
    return;
  }

  if (data.type === "ZIDER_QUICK_ACTION") {
    const { action, text, pageUrl } = data;
    if (action === "explain") {
      switchTab("tab-chat");
      chatInput.value = `Explain the following text simply and clearly:\n\n"${text}"`;
      sendChatMessage();
    } else if (action === "summarize") {
      switchTab("tab-read");
      readSummaryOutput.textContent = "Summarizing selected text...";
      summarizeText(text);
    } else if (action === "translate") {
      switchTab("tab-translate");
      transInput.value = text;
      runTranslation();
    } else if (action === "grammar") {
      switchTab("tab-write");
      writeTaskSelect.value = "grammar";
      writeInput.value = text;
      runWrite();
    } else if (action === "reply") {
      switchTab("tab-write");
      writeTaskSelect.value = "reply";
      writeInput.value = text;
      runWrite();
    } else if (action === "chat") {
      switchTab("tab-chat");
      chatInput.value = `Regarding this context:\n"${text}"\n\n`;
      chatInput.focus();
    } else if (action === "summarize_page") {
      switchTab("tab-read");
      summarizeActivePage(pageUrl);
    }
  }
});
