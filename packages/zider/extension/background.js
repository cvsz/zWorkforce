/**
 * zider Background Service Worker (Manifest V3)
 * Orchestrates context menus, hotkeys, screenshot capture, and tab messaging.
 */

// Initialize Context Menu Items on Install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "zider-explain",
    title: "zider: Explain '%s'",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "zider-summarize",
    title: "zider: Summarize selection",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "zider-translate",
    title: "zider: Translate selection",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "zider-grammar",
    title: "zider: Fix grammar & rewrite",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "zider-summarize-page",
    title: "zider: Summarize this entire page",
    contexts: ["page"]
  });

  chrome.contextMenus.create({
    id: "zider-capture-vision",
    title: "zider: Snip area & Analyze with Vision AI",
    contexts: ["page"]
  });
});

// Handle Context Menu Actions
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (!tab || !tab.id) return;

  if (info.menuItemId === "zider-capture-vision") {
    captureTabScreenshot(tab.id);
    return;
  }

  const actionMap = {
    "zider-explain": "explain",
    "zider-summarize": "summarize",
    "zider-translate": "translate",
    "zider-grammar": "grammar",
    "zider-summarize-page": "summarize_page"
  };

  const action = actionMap[info.menuItemId];
  if (action) {
    chrome.tabs.sendMessage(tab.id, {
      type: "ZIDER_CONTEXT_ACTION",
      action: action,
      selectedText: info.selectionText || ""
    });
  }
});

// Capture Visible Tab Screenshot for Vision/OCR
function captureTabScreenshot(tabId) {
  chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
    if (chrome.runtime.lastError || !dataUrl) return;
    chrome.tabs.sendMessage(tabId, {
      type: "ZIDER_SCREENSHOT_CAPTURED",
      dataUrl: dataUrl
    });
  });
}

// Handle Messages from Content Script or Sidebar
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "ZIDER_CAPTURE_TAB_REQUEST") {
    if (sender.tab && sender.tab.id) {
      captureTabScreenshot(sender.tab.id);
    } else {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0] && tabs[0].id) {
          captureTabScreenshot(tabs[0].id);
        }
      });
    }
  }
});

// Handle Global Keyboard Commands (e.g. Ctrl+M / Cmd+M)
chrome.commands.onCommand.addListener((command) => {
  if (command === "toggle-sidebar") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs.length > 0 && tabs[0].id) {
        chrome.tabs.sendMessage(tabs[0].id, { type: "ZIDER_TOGGLE_SIDEBAR" });
      }
    });
  }
});
