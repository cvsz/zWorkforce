/**
 * zider Content Script (v1.2)
 * Injects Closed Shadow DOM Sidebar, Selection Toolbar, Inline Input Helper, Full Page Translator, and Reader View
 */

(function () {
  if (window.__zider_initialized) return;
  window.__zider_initialized = true;

  // Create Shadow Host Container
  const host = document.createElement("div");
  host.id = "zider-companion-root";
  host.style.cssText = "all: initial; position: fixed; top: 0; right: 0; z-index: 2147483647;";
  document.documentElement.appendChild(host);

  const shadow = host.attachShadow({ mode: "open" });

  // Stylesheet injection into Shadow DOM
  const style = document.createElement("style");
  style.textContent = `
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    
    #zider-toggle-btn {
      position: fixed;
      right: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 34px;
      height: 52px;
      background: #18181b;
      border: 1px solid #27272a;
      border-right: none;
      border-radius: 10px 0 0 10px;
      color: #fafafa;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: -4px 0 15px rgba(0,0,0,0.4);
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      z-index: 2147483647;
      user-select: none;
      gap: 2px;
    }
    #zider-toggle-btn:hover {
      width: 42px;
      background: #27272a;
      color: #38bdf8;
    }
    .toggle-icon { font-size: 16px; }
    .toggle-label { font-size: 8px; font-weight: 700; color: #38bdf8; letter-spacing: 0.5px; }
    
    #zider-iframe-wrapper {
      position: fixed;
      top: 0;
      right: -490px;
      width: 470px;
      height: 100vh;
      background: #09090b;
      box-shadow: -8px 0 30px rgba(0,0,0,0.6);
      border-left: 1px solid #27272a;
      transition: right 0.28s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      flex-direction: column;
      z-index: 2147483646;
    }
    
    #zider-iframe-wrapper.open {
      right: 0;
    }

    #zider-frame {
      width: 100%;
      height: 100%;
      border: none;
      background: transparent;
    }

    /* Floating Quick Bar on Text Selection */
    #zider-selection-bar {
      position: fixed;
      display: none;
      background: #18181b;
      border: 1px solid #3f3f46;
      border-radius: 8px;
      padding: 4px;
      gap: 4px;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5);
      z-index: 2147483647;
      align-items: center;
    }
    .zider-quick-btn {
      background: transparent;
      border: none;
      color: #d4d4d8;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: background 0.15s ease, color 0.15s ease;
    }
    .zider-quick-btn:hover {
      background: #27272a;
      color: #38bdf8;
    }

    /* Inline Input Floating AI Badge */
    #zider-inline-badge {
      position: absolute;
      display: none;
      background: #18181b;
      border: 1px solid #38bdf8;
      color: #38bdf8;
      border-radius: 12px;
      padding: 3px 8px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
      z-index: 2147483647;
      align-items: center;
      gap: 4px;
      transition: transform 0.15s;
    }
    #zider-inline-badge:hover {
      transform: scale(1.05);
      background: #27272a;
    }

    /* Full Page Reader Mode Overlay */
    #zider-reader-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: #09090b;
      color: #f4f4f5;
      z-index: 2147483640;
      display: none;
      overflow-y: auto;
      padding: 40px 20px;
    }
    .reader-container {
      max-width: 720px;
      margin: 0 auto;
      line-height: 1.8;
      font-size: 17px;
    }
    .reader-close {
      position: fixed;
      top: 20px;
      right: 20px;
      background: #27272a;
      color: #fff;
      border: 1px solid #3f3f46;
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
    }
  `;
  shadow.appendChild(style);

  // Toggle button
  const toggleBtn = document.createElement("div");
  toggleBtn.id = "zider-toggle-btn";
  toggleBtn.innerHTML = `
    <span class="toggle-icon">⚡</span>
    <span class="toggle-label">ZIDER</span>
  `;
  toggleBtn.title = "Toggle zider Sidebar (Ctrl+M / Cmd+M)";
  shadow.appendChild(toggleBtn);

  // Sidebar container
  const wrapper = document.createElement("div");
  wrapper.id = "zider-iframe-wrapper";
  
  const iframe = document.createElement("iframe");
  iframe.id = "zider-frame";
  iframe.src = chrome.runtime.getURL("sidebar.html");
  wrapper.appendChild(iframe);
  shadow.appendChild(wrapper);

  // Selection Quick Toolbar
  const selBar = document.createElement("div");
  selBar.id = "zider-selection-bar";
  selBar.innerHTML = `
    <button class="zider-quick-btn" data-act="explain">📖 Explain</button>
    <button class="zider-quick-btn" data-act="summarize">📝 Summarize</button>
    <button class="zider-quick-btn" data-act="translate">🌐 Translate</button>
    <button class="zider-quick-btn" data-act="grammar">✍️ Fix Grammar</button>
    <button class="zider-quick-btn" data-act="chat">💬 Ask AI</button>
  `;
  shadow.appendChild(selBar);

  // Inline Input AI Badge
  const inlineBadge = document.createElement("div");
  inlineBadge.id = "zider-inline-badge";
  inlineBadge.innerHTML = `⚡ AI Write`;
  inlineBadge.title = "Click to draft, improve or reply with zider AI";
  shadow.appendChild(inlineBadge);

  // Reader Mode Overlay
  const readerOverlay = document.createElement("div");
  readerOverlay.id = "zider-reader-overlay";
  readerOverlay.innerHTML = `
    <button class="reader-close" id="reader-close-btn">✕ Exit Reader Mode</button>
    <div class="reader-container" id="reader-article-content"></div>
  `;
  shadow.appendChild(readerOverlay);

  let isSidebarOpen = false;
  let activeFocusedInput = null;

  function toggleSidebar(forceState) {
    isSidebarOpen = forceState !== undefined ? forceState : !isSidebarOpen;
    if (isSidebarOpen) {
      wrapper.classList.add("open");
    } else {
      wrapper.classList.remove("open");
    }
  }

  toggleBtn.addEventListener("click", () => toggleSidebar());

  // Text selection handler
  let activeSelection = "";
  document.addEventListener("mouseup", () => {
    setTimeout(() => {
      const selection = window.getSelection();
      const text = selection ? selection.toString().trim() : "";
      if (text.length > 2) {
        activeSelection = text;
        try {
          const range = selection.getRangeAt(0);
          const rect = range.getBoundingClientRect();
          selBar.style.top = `${Math.max(10, rect.top - 45)}px`;
          selBar.style.left = `${Math.min(window.innerWidth - 400, Math.max(10, rect.left))}px`;
          selBar.style.display = "flex";
        } catch (e) {}
      } else {
        selBar.style.display = "none";
      }
    }, 50);
  });

  document.addEventListener("mousedown", (e) => {
    if (!host.contains(e.target)) {
      selBar.style.display = "none";
    }
  });

  // Handle click on selection quick buttons
  selBar.addEventListener("click", (e) => {
    const btn = e.target.closest(".zider-quick-btn");
    if (!btn) return;
    const act = btn.getAttribute("data-act");
    selBar.style.display = "none";
    toggleSidebar(true);

    if (iframe.contentWindow) {
      iframe.contentWindow.postMessage({
        type: "ZIDER_QUICK_ACTION",
        action: act,
        text: activeSelection,
        pageUrl: window.location.href,
        pageTitle: document.title
      }, "*");
    }
  });

  // Inline Input Focus Listener (Gmail, GitHub, Twitter, Textareas)
  document.addEventListener("focusin", (e) => {
    const el = e.target;
    if (
      el &&
      (el.tagName === "TEXTAREA" ||
       (el.tagName === "INPUT" && el.type === "text") ||
       el.isContentEditable)
    ) {
      activeFocusedInput = el;
      const rect = el.getBoundingClientRect();
      inlineBadge.style.top = `${window.scrollY + rect.top + 6}px`;
      inlineBadge.style.left = `${window.scrollX + rect.right - 85}px`;
      inlineBadge.style.display = "flex";
    }
  });

  inlineBadge.addEventListener("click", () => {
    if (!activeFocusedInput) return;
    const currentVal = activeFocusedInput.value || activeFocusedInput.innerText || "";
    toggleSidebar(true);
    if (iframe.contentWindow) {
      iframe.contentWindow.postMessage({
        type: "ZIDER_QUICK_ACTION",
        action: currentVal.length > 0 ? "grammar" : "reply",
        text: currentVal,
        pageUrl: window.location.href,
        pageTitle: document.title
      }, "*");
    }
  });

  // Reader Mode
  function enterReaderMode() {
    const title = document.title;
    const paragraphs = Array.from(document.querySelectorAll("p, article, h1, h2, h3"))
      .map(p => p.outerHTML)
      .join("");
    
    shadow.getElementById("reader-article-content").innerHTML = `
      <h1 style="font-size:28px;margin-bottom:20px;color:#38bdf8;">${title}</h1>
      <div style="color:#d4d4d8;">${paragraphs || "No article content detected."}</div>
    `;
    readerOverlay.style.display = "block";
  }

  shadow.getElementById("reader-close-btn").addEventListener("click", () => {
    readerOverlay.style.display = "none";
  });

  // In-Place Full Page Translation
  let isPageBilingualTranslated = false;
  async function toggleBilingualPageTranslation(targetLang = "es") {
    if (isPageBilingualTranslated) {
      document.querySelectorAll(".zider-translated-para").forEach(el => el.remove());
      isPageBilingualTranslated = false;
      return;
    }

    const paragraphs = Array.from(document.querySelectorAll("p")).slice(0, 25);
    const texts = paragraphs.map(p => p.innerText.trim()).filter(t => t.length > 10);
    if (texts.length === 0) return;

    try {
      const res = await fetch("http://127.0.0.1:8085/api/translate/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: texts, target_lang: targetLang })
      });
      const data = await res.json();
      
      let idx = 0;
      paragraphs.forEach(p => {
        if (p.innerText.trim().length > 10 && idx < data.items.length) {
          const tDiv = document.createElement("div");
          tDiv.className = "zider-translated-para";
          tDiv.style.cssText = "color: #38bdf8; font-size: 0.95em; margin: 4px 0 10px 0; border-left: 2px solid #38bdf8; padding-left: 8px; font-style: italic;";
          tDiv.innerText = data.items[idx];
          p.after(tDiv);
          idx++;
        }
      });
      isPageBilingualTranslated = true;
    } catch (e) {
      console.warn("zider page translation error:", e);
    }
  }

  // Listen for messages from background service worker
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === "ZIDER_TOGGLE_SIDEBAR") {
      toggleSidebar();
    } else if (msg.type === "ZIDER_CONTEXT_ACTION") {
      toggleSidebar(true);
      if (iframe.contentWindow) {
        iframe.contentWindow.postMessage({
          type: "ZIDER_QUICK_ACTION",
          action: msg.action,
          text: msg.selectedText || "",
          pageUrl: window.location.href,
          pageTitle: document.title
        }, "*");
      }
    } else if (msg.type === "ZIDER_SCREENSHOT_CAPTURED") {
      toggleSidebar(true);
      if (iframe.contentWindow) {
        iframe.contentWindow.postMessage({
          type: "ZIDER_SCREENSHOT_IMAGE",
          dataUrl: msg.dataUrl
        }, "*");
      }
    }
  });

  // Handle messages from sidebar iframe
  window.addEventListener("message", (e) => {
    if (!e.data) return;
    if (e.data.type === "ZIDER_CAPTURE_SNIP_REQUEST") {
      chrome.runtime.sendMessage({ type: "ZIDER_CAPTURE_TAB_REQUEST" });
    } else if (e.data.type === "ZIDER_INSERT_TEXT_TO_INPUT" && activeFocusedInput) {
      if (activeFocusedInput.value !== undefined) {
        activeFocusedInput.value = e.data.text;
      } else if (activeFocusedInput.innerText !== undefined) {
        activeFocusedInput.innerText = e.data.text;
      }
    } else if (e.data.type === "ZIDER_TRIGGER_READER_MODE") {
      enterReaderMode();
    } else if (e.data.type === "ZIDER_TRIGGER_PAGE_TRANSLATE") {
      toggleBilingualPageTranslation(e.data.targetLang || "es");
    }
  });
})();
