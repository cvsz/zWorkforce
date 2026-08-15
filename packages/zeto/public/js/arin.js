/**
 * Arin — Zeto's anime AI companion (Jarvis-style push-to-talk assistant).
 * Self-contained module: no dependencies on app.js internals.
 */
(function () {
  "use strict";

  // ── DOM refs ────────────────────────────────────────────────────────────────
  const orb = document.getElementById("arin-orb");
  const panel = document.getElementById("arin-panel");
  const closeBtn = document.getElementById("arin-close");
  const messages = document.getElementById("arin-messages");
  const input = document.getElementById("arin-input");
  const sendBtn = document.getElementById("arin-send");
  const micBtn = document.getElementById("arin-mic");
  const statusEl = document.getElementById("arin-status");
  const avatar = document.querySelector(".arin-avatar");

  // ── Feature detection ──────────────────────────────────────────────────────
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  const hasSpeech = !!SpeechRecognition;
  const hasTTS = "speechSynthesis" in window;

  // ── State ───────────────────────────────────────────────────────────────────
  let open = false;
  let listening = false;
  let speaking = false;
  let recognition = null;
  let interimText = "";
  let greetingShown = false;
  let preferredLang = "en-US";

  const THAI_RE = /[\u0E00-\u0E7F]/;

  // ── Persona ─────────────────────────────────────────────────────────────────
  const PERSONA = {
    name: "Arin",
    greeting:
      "Heya! I'm Arin, your anime AI assistant. Hold the mic and talk to me, or type a command like “queue status”!",
    help: [
      "Here's what I can do for you, nya~",
      "• “Status” — server + scheduler health",
      "• “Queue” — what's waiting to publish",
      "• “Pending review” — items needing approval",
      "• “Go to settings / queue / analytics…” — jump to a page",
      "• “Who are you” — about me",
    ],
  };

  const BANTER = [
    "Mmm, I'm still learning that trick. Try “queue”, “status”, or “go to analytics”!",
    "That one's beyond my circuits for now, but I'm always watching, always listening. Try a dashboard command!",
    "Ooh, interesting… I can't do that yet, but ask me about the queue or pending reviews!",
    "My sensors didn't catch that. Hold the mic and try again, or type a command like “status”!",
  ];

  // ── API helper (mirrors app.js, self-contained) ────────────────────────────
  async function api(method, path) {
    const token = localStorage.getItem("zeto_token");
    const opts = { method, headers: {} };
    if (token) opts.headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(path, opts);
    let json = null;
    try {
      json = await res.json();
    } catch {
      /* non-JSON response */
    }
    if (res.status === 401) {
      throw new Error("You need to log in first, senpai.");
    }
    if (!res.ok && (!json || !json.ok)) {
      throw new Error(json?.error?.message || `Request failed (${res.status})`);
    }
    return json || { ok: res.ok };
  }

  // ── Chat UI ─────────────────────────────────────────────────────────────────
  function addMsg(text, who, extraClass) {
    const el = document.createElement("div");
    el.className = `arin-msg ${who}${extraClass ? " " + extraClass : ""}`;
    if (who === "arin" && hasTTS && extraClass !== "error") {
      el.innerHTML = `<span class="arin-msg-emoji">✦</span><span></span>`;
      el.lastElementChild.textContent = text;
    } else {
      el.textContent = text;
    }
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }

  function addUser(text) {
    addMsg(text, "user");
  }

  function addArin(text, extraClass) {
    const el = addMsg(text, "arin", extraClass);
    if (extraClass !== "error") speak(text);
    return el;
  }

  function addTyping() {
    const el = document.createElement("div");
    el.className = "arin-msg arin typing";
    el.innerHTML =
      '<span class="arin-typing-dots"><span>●</span><span>●</span><span>●</span></span>';
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }

  function setStatus(text, cls) {
    statusEl.textContent = text;
    statusEl.className = "arin-status" + (cls ? " " + cls : "");
  }

  // ── Speech synthesis (anime-style voice) ───────────────────────────────────
  function pickVoice() {
    if (!hasTTS) return null;
    const voices = window.speechSynthesis.getVoices();
    const prefs = [
      /ja[-_]JP|Google 日本語|Haruka|Sayaka|Ayumi|Nanami|Kyoko/i,
      /Google UK English Female|Samantha|Victoria|Karen|Moira/i,
      /female/i,
      /en[-_]/i,
    ];
    for (const re of prefs) {
      const v = voices.find((v) => re.test(v.name));
      if (v) return v;
    }
    return voices[0] || null;
  }

  function speak(text) {
    if (!hasTTS) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = pickVoice();
    if (voice) utterance.voice = voice;
    utterance.lang = voice?.lang || preferredLang;
    utterance.rate = 1.02;
    utterance.pitch = 1.15;
    speaking = true;
    orb.classList.add("speaking");
    avatar.classList.add("speaking");
    setStatus("Speaking…", "speaking");
    utterance.onend = () => {
      speaking = false;
      orb.classList.remove("speaking");
      avatar.classList.remove("speaking");
      setStatus("Standby");
    };
    utterance.onerror = () => {
      speaking = false;
      orb.classList.remove("speaking");
      avatar.classList.remove("speaking");
      setStatus("Standby");
    };
    window.speechSynthesis.speak(utterance);
  }

  // ── Push-to-talk speech recognition ────────────────────────────────────────
  function startListening() {
    if (!hasSpeech) return;
    if (listening) return;
    if (speaking) window.speechSynthesis.cancel();
    recognition = new SpeechRecognition();
    recognition.lang = preferredLang;
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      listening = true;
      micBtn.classList.add("listening");
      orb.classList.add("listening");
      setStatus("Listening… hold to talk", "listening");
      interimText = "";
    };
    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          handleInput(transcript.trim());
          return;
        }
        interim += transcript;
      }
      interimText = interim;
      input.value = interim;
    };
    recognition.onerror = (event) => {
      if (
        event.error === "not-allowed" ||
        event.error === "service-not-allowed"
      ) {
        setStatus("Mic permission denied");
        toastish("Arin needs mic permission to hear you.");
      } else if (event.error !== "aborted" && event.error !== "no-speech") {
        setStatus("Mic error: " + event.error);
      }
    };
    recognition.onend = () => {
      listening = false;
      micBtn.classList.remove("listening");
      orb.classList.remove("listening");
      if (interimText && !input.dataset.handled) {
        handleInput(interimText.trim());
      }
      interimText = "";
      input.value = "";
      if (!speaking) setStatus("Standby");
    };
    try {
      recognition.start();
    } catch {
      /* already started */
    }
  }

  function stopListening() {
    if (!listening) return;
    input.dataset.handled = "";
    try {
      recognition.stop();
    } catch {
      /* ignore */
    }
  }

  // ── Command engine ──────────────────────────────────────────────────────────
  const PAGE_ALIASES = {
    dashboard: "dashboard",
    overview: "dashboard",
    home: "dashboard",
    analytics: "analytics",
    stats: "analytics",
    compose: "compose",
    queue: "queue",
    scheduler: "scheduler",
    schedule: "scheduler",
    feed: "feed",
    history: "history",
    settings: "settings",
    ai: "ai",
    "ai generator": "ai",
    "control room": "control-room",
    "control-room": "control-room",
  };

  async function handleInput(raw) {
    const text = (raw || "").replace(/[.?!,，。！？]+$/, "").trim();
    if (!text) return;
    if (THAI_RE.test(text)) preferredLang = "th-TH";
    addUser(text);
    const typing = addTyping();

    let reply;
    try {
      reply = await respond(text);
    } catch (err) {
      reply = { text: err.message, error: true };
    }

    typing.remove();
    if (reply.error) {
      addArin(reply.text, "error");
    } else {
      addArin(reply.text);
    }
  }

  async function respond(text) {
    const t = text.toLowerCase();

    if (
      /^(hi|hello|hey|yo|hola|สวัสดี|หวัดดี|ไง)\b/.test(t) ||
      t === "hi" ||
      t === "hello"
    ) {
      return {
        text: "Heya! Ready when you are — hold the mic or type a command.",
      };
    }
    if (/(who are you|what are you|about you|你是谁)/.test(t)) {
      return {
        text: "I'm Arin — Zeto's AI companion. Think Jarvis with a dash of anime energy. I watch over your queue, approvals, and publishing health so you don't have to!",
      };
    }
    if (/(what can you do|help|commands|ช่วย)/.test(t)) {
      return { text: PERSONA.help.join(" ") };
    }
    if (/(go to|open|show me|take me to|navigate to)\s+(.+)/.test(t)) {
      const target = t
        .match(/(?:go to|open|show me|take me to|navigate to)\s+(.+)/)[1]
        .trim();
      const page =
        PAGE_ALIASES[target] || PAGE_ALIASES[target.replace(/s$/, "")];
      if (page) {
        const link = document.querySelector(`.nav-link[data-page="${page}"]`);
        if (link) {
          link.click();
          return { text: `Opening ${page} for you! ✨` };
        }
      }
      return {
        text: `I don't know a page called “${target}”. Try queue, analytics, settings, or history.`,
      };
    }
    if (/(status|health|are you (online|up)|server|ระบบ)/.test(t)) {
      const h = await api("GET", "/health");
      const sched = h.scheduler || {};
      const schedState = sched.running
        ? "running"
        : sched.enabled
          ? "enabled"
          : "idle";
      return {
        text: `All systems green! Server up for ${h.uptime} seconds, version ${h.version}. Scheduler is ${schedState}${sched.cron ? " with cron " + sched.cron : ""}.`,
      };
    }
    if (/(pending review|approvals?|needs? approval|รออนุมัติ)/.test(t)) {
      const res = await api("GET", "/api/queue/pending-review");
      const items = res.data || [];
      if (!items.length)
        return {
          text: "Nothing waiting for approval — your pipeline is all clear! ⭐",
        };
      return {
        text: `You have ${items.length} item${items.length === 1 ? "" : "s"} awaiting review. ${items
          .slice(0, 3)
          .map((i) => `“${i.title || i.message || "untitled"}”`)
          .join(", ")}.`,
      };
    }
    if (/(queue|คิว)/.test(t)) {
      const res = await api("GET", "/api/queue");
      const items = res.data || [];
      if (!items.length)
        return {
          text: "Your queue is empty — nothing scheduled right now. 💤",
        };
      const pending = items.filter((i) => i.status === "pending").length;
      const scheduled = items.filter((i) => i.status === "scheduled").length;
      return {
        text: `You have ${items.length} item${items.length === 1 ? "" : "s"} in the queue — ${pending} pending, ${scheduled} scheduled. ${items
          .slice(0, 2)
          .map((i) => `“${i.title || i.message || "untitled"}”`)
          .join(", ")}${items.length > 2 ? "…" : ""}`,
      };
    }
    if (/(history|ประวัติ)/.test(t)) {
      const res = await api("GET", "/api/history");
      const items = res.data || [];
      return {
        text: items.length
          ? `You have ${items.length} past publications logged. Want me to open History?`
          : "No publication history yet — go make some noise!",
      };
    }
    if (/(thank|thanks|ขอบคุณ)/.test(t)) {
      return { text: "Anytime! I'll always be here, watching the feed. ♡" };
    }
    if (/(bye|goodbye|good night|ลาก่อน)/.test(t)) {
      return {
        text: "See you soon! I'll keep an eye on the queue for you. 👋",
      };
    }
    return { text: BANTER[Math.floor(Math.random() * BANTER.length)] };
  }

  // ── Panel open/close ────────────────────────────────────────────────────────
  function openPanel() {
    open = true;
    panel.classList.add("open");
    orb.classList.add("open");
    if (!greetingShown) {
      greetingShown = true;
      setTimeout(() => {
        addArin(PERSONA.greeting);
      }, 350);
    }
    setTimeout(() => input.focus(), 250);
  }

  function closePanel() {
    open = false;
    panel.classList.remove("open");
    orb.classList.remove("open");
    if (listening) stopListening();
    if (speaking) window.speechSynthesis.cancel();
    setStatus("Standby");
  }

  // ── Events ──────────────────────────────────────────────────────────────────
  orb.addEventListener("click", () => (open ? closePanel() : openPanel()));
  closeBtn.addEventListener("click", closePanel);

  function sendFromInput() {
    const value = input.value.trim();
    if (!value) return;
    input.value = "";
    handleInput(value);
  }

  sendBtn.addEventListener("click", sendFromInput);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendFromInput();
  });

  // Push-to-talk: hold to talk, release to send
  micBtn.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    if (!hasSpeech) return;
    startListening();
  });
  ["pointerup", "pointercancel", "lostpointercapture"].forEach((evt) =>
    micBtn.addEventListener(evt, stopListening),
  );

  // ── Helpers ─────────────────────────────────────────────────────────────────
  function toastish(msg) {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const el = document.createElement("div");
    el.className = "toast warning";
    el.innerHTML = `<span>${msg}</span>`;
    container.appendChild(el);
    setTimeout(() => {
      el.style.animation = "slideOut 0.3s ease forwards";
      setTimeout(() => el.remove(), 300);
    }, 4000);
  }

  function loadVoices() {
    if (hasTTS) window.speechSynthesis.getVoices();
  }

  // ── Init ────────────────────────────────────────────────────────────────────
  if (!hasSpeech) {
    micBtn.disabled = true;
    micBtn.title = "Speech recognition not supported in this browser";
    micBtn.style.opacity = "0.4";
    document.querySelector(".arin-hint").textContent =
      "Speech input isn't supported here — type a command instead. Try: “What's in my queue?”";
  }
  if (hasTTS) {
    loadVoices();
    if ("onvoiceschanged" in window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }
})();
