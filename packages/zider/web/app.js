// Standalone Web App Logic
const API_HOST = "http://127.0.0.1:8085";

const navBtns = document.querySelectorAll(".nav-btn");
const viewPanels = document.querySelectorAll(".view-panel");

navBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    navBtns.forEach((b) => b.classList.remove("active"));
    viewPanels.forEach((p) => p.classList.remove("active"));

    btn.classList.add("active");
    const view = btn.getAttribute("data-view");
    const panel = document.getElementById(`view-${view}`);
    if (panel) panel.classList.add("active");
  });
});

const composerInput = document.getElementById("composer-input");
const composerSend = document.getElementById("composer-send");
const chatFlow = document.getElementById("chat-flow");
const modelSelect = document.getElementById("model-select");

async function handleWebChat() {
  const text = composerInput.value.trim();
  if (!text) return;

  const uDiv = document.createElement("div");
  uDiv.className = "chat-msg user";
  uDiv.innerHTML = `<div class="content">${text}</div>`;
  chatFlow.appendChild(uDiv);
  composerInput.value = "";

  const aDiv = document.createElement("div");
  aDiv.className = "chat-msg assistant";
  aDiv.innerHTML = `<div class="avatar">⚡</div><div class="content">Thinking...</div>`;
  chatFlow.appendChild(aDiv);
  const bubble = aDiv.querySelector(".content");

  try {
    const res = await fetch(`${API_HOST}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: modelSelect.value,
        messages: [{ role: "user", content: text }]
      })
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    bubble.textContent = "";

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
            if (parsed.delta) bubble.textContent += parsed.delta;
          } catch (e) {}
        }
      }
    }
  } catch (err) {
    bubble.textContent = `Error: ${err.message}`;
  }
}

composerSend.addEventListener("click", handleWebChat);
composerInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleWebChat();
  }
});
