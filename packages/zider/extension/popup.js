document.getElementById("toggle-btn").addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs.length > 0 && tabs[0].id) {
      chrome.tabs.sendMessage(tabs[0].id, { type: "ZIDER_TOGGLE_SIDEBAR" });
      window.close();
    }
  });
});
