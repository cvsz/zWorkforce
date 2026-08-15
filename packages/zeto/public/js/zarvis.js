(() => {
  "use strict";

  const canvas = document.getElementById("zarvis-canvas");
  const ctx = canvas.getContext("2d", { alpha: false });
  const OperatorStream = window.OperatorStream;
  const {
    parseSseBlocks,
    parseEventData,
    streamEntryFromEvent,
    orbPresentationForState,
  } = OperatorStream;

  // ── M11 point-cloud renderer state ──────────────────────────────────────────
  let points = [];
  let state = null;
  let frame = 0;

  // ── M12 operator session state ──────────────────────────────────────────────
  const SESSION_KEY = "zeto_zarvis_session";
  const STREAM_KEY = "zeto_zarvis_stream";
  let session = { id: null, lastEventId: 0, state: "IDLE" };
  let streamEntries = [];
  let streamAbort = null;
  let reconnectAttempt = 0;
  let connecting = false;

  function persistStream() {
    try {
      localStorage.setItem(
        STREAM_KEY,
        JSON.stringify(streamEntries.slice(-100)),
      );
    } catch {
      /* storage unavailable */
    }
  }

  function loadStoredStream() {
    try {
      const raw = localStorage.getItem(STREAM_KEY);
      if (raw) streamEntries = JSON.parse(raw) || [];
    } catch {
      streamEntries = [];
    }
  }

  function getToken() {
    return (
      localStorage.getItem("zeto_token") ||
      localStorage.getItem("zfbauto_token")
    );
  }

  function persistSession() {
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } catch {
      /* storage unavailable */
    }
  }

  function loadStoredSession() {
    try {
      const raw = localStorage.getItem(SESSION_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && parsed.id) {
          session = {
            id: parsed.id,
            lastEventId: Number(parsed.lastEventId) || 0,
            state: parsed.state || "IDLE",
          };
          return true;
        }
      }
    } catch {
      /* corrupt storage */
    }
    return false;
  }

  // ── Connection pill ─────────────────────────────────────────────────────────
  function setConnection(label, cls) {
    const pill = document.getElementById("connection-pill");
    if (!pill) return;
    pill.textContent = label;
    pill.className = `pill ${cls}`;
  }

  // ── Orb state presentation (spec §2.3) ──────────────────────────────────────
  function renderOrbState() {
    const el = document.getElementById("orb-state");
    if (!el) return;
    const presentation = orbPresentationForState(session.state);
    el.dataset.tone = presentation.tone;
    el.textContent =
      session.state === "IDLE"
        ? "JARVIS CORE / WAITING FOR INPUT"
        : presentation.label;
    const status = document.getElementById("stream-status");
    if (status) status.textContent = presentation.label;
  }

  // ── Command stream (spec §4.2, §2.4) ───────────────────────────────────────
  function appendStreamEntry(entry) {
    if (!entry) return;
    const list = document.getElementById("command-stream");
    if (!list) return;
    const empty = list.querySelector(".stream-empty");
    if (empty) empty.remove();

    const li = document.createElement("li");
    li.className = "stream-entry";
    li.dataset.result = entry.result;

    const actor = document.createElement("span");
    actor.className = "entry-actor";
    actor.textContent = entry.actor || "system";

    const summary = document.createElement("span");
    summary.className = "entry-summary";
    summary.textContent = entry.summary || entry.type || "event";

    const meta = document.createElement("span");
    meta.className = "entry-meta";
    meta.textContent = entry.ts ? new Date(entry.ts).toLocaleTimeString() : "";

    const result = document.createElement("span");
    result.className = "entry-result";
    result.textContent = entry.result || "ok";

    li.append(actor, summary, meta, result);

    if (entry.error) {
      const error = document.createElement("span");
      error.className = "entry-error";
      error.textContent = `Recovery: ${entry.error}`;
      li.appendChild(error);
    }

    list.appendChild(li);

    // Keep the newest entries visible.
    const nearBottom =
      list.scrollHeight - list.scrollTop - list.clientHeight < 48;
    if (nearBottom) list.scrollTop = list.scrollHeight;
  }

  function renderStreamEntries() {
    const list = document.getElementById("command-stream");
    if (!list) return;
    list.innerHTML = "";
    if (!streamEntries.length) {
      const empty = document.createElement("li");
      empty.className = "stream-empty";
      empty.textContent = "No commands yet";
      list.appendChild(empty);
      return;
    }
    for (const entry of streamEntries) appendStreamEntry(entry);
    list.scrollTop = list.scrollHeight;
  }

  function addStreamError(message) {
    const list = document.getElementById("command-stream");
    if (!list) return;
    const empty = list.querySelector(".stream-empty");
    if (empty) empty.remove();
    const li = document.createElement("li");
    li.className = "stream-entry";
    li.dataset.result = "error";
    const summary = document.createElement("span");
    summary.className = "entry-summary";
    summary.textContent = message;
    const result = document.createElement("span");
    result.className = "entry-result";
    result.textContent = "error";
    li.append(summary, result);
    list.appendChild(li);
  }

  // ── Event handling (spec §10 catalog) ───────────────────────────────────────
  function handleEvent(event) {
    if (!event || !event.event_id) return;
    session.lastEventId = Math.max(
      session.lastEventId,
      Number(event.sequence_id) || 0,
    );
    if (event.type === "session.state_changed") {
      session.state = event.payload?.to || session.state;
      persistSession();
      renderOrbState();
    }
    const entry = streamEntryFromEvent(event);
    if (entry) {
      streamEntries.push(entry);
      if (streamEntries.length > 500) streamEntries = streamEntries.slice(-500);
      appendStreamEntry(entry);
      persistStream();
    }
    persistSession();
  }

  // ── SSE via fetch (EventSource cannot send the Authorization header) ───────
  async function connectStream() {
    if (!session.id || connecting) return;
    connecting = true;
    if (streamAbort) streamAbort.abort();
    streamAbort = new AbortController();
    setConnection("CONNECTING", "offline");

    const url = `/v1/operator/sessions/${session.id}/events`;
    try {
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${getToken()}`,
          "Last-Event-ID": String(session.lastEventId || 0),
        },
        signal: streamAbort.signal,
        cache: "no-store",
      });
      if (response.status === 401) {
        setConnection("AUTH REQUIRED", "offline");
        addStreamError("Authentication expired — reconnect the dashboard.");
        return;
      }
      if (response.status === 404) {
        setConnection("SESSION GONE", "offline");
        addStreamError("Operator session no longer exists — create a new one.");
        session = { id: null, lastEventId: 0, state: "IDLE" };
        persistSession();
        return;
      }
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      reconnectAttempt = 0;
      setConnection("LIVE", "online");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // Only parse complete blocks (separated by a blank line); keep the
        // trailing partial block buffered so it is parsed exactly once.
        const parts = buffer.split(/\r?\n\r?\n/);
        buffer = parts.pop() || "";
        for (const part of parts) {
          if (!part.trim()) continue;
          const [block] = parseSseBlocks(part);
          const event = block ? parseEventData(block.data) : null;
          if (event) handleEvent(event);
        }
      }
    } catch (error) {
      if (error.name === "AbortError") return;
      scheduleReconnect();
    } finally {
      connecting = false;
      if (!streamAbort.signal.aborted) {
        setConnection("RECONNECTING", "offline");
        scheduleReconnect();
      }
    }
  }

  function scheduleReconnect() {
    const delay = Math.min(1000 * 2 ** reconnectAttempt, 30000);
    reconnectAttempt += 1;
    setTimeout(connectStream, delay);
  }

  // ── Session lifecycle ───────────────────────────────────────────────────────
  async function createSession(force = false) {
    if (!force && loadStoredSession() && session.id) {
      try {
        const response = await fetch(`/v1/operator/sessions/${session.id}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
          cache: "no-store",
        });
        if (response.ok) {
          const body = await response.json();
          if (body.data) {
            session.state = body.data.state || session.state;
            persistSession();
            renderOrbState();
            connectStream();
            return;
          }
        }
      } catch {
        /* fall through to create */
      }
    }

    const response = await fetch("/v1/operator/sessions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${getToken()}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ mode: "operator", capabilities: [] }),
    });
    if (response.status === 403) {
      setConnection("VIEW ONLY", "offline");
      addStreamError(
        "Operator session requires editor access — commands are read-only for this account.",
      );
      return;
    }
    if (response.status === 401) {
      setConnection("AUTH REQUIRED", "offline");
      return;
    }
    if (!response.ok) {
      setConnection("OFFLINE", "offline");
      addStreamError(
        `Could not start operator session (HTTP ${response.status}).`,
      );
      return;
    }
    const body = await response.json();
    session = {
      id: body.data.session.id,
      lastEventId: body.data.sequence_id || 0,
      state: body.data.session.state || "IDLE",
    };
    persistSession();
    streamEntries = [];
    persistStream();
    renderStreamEntries();
    renderOrbState();
    connectStream();
  }

  // ── Command submission ──────────────────────────────────────────────────────
  async function submitCommand() {
    const input = document.getElementById("command-input");
    const text = (input.value || "").trim();
    if (!text || !session.id) return;
    input.value = "";
    try {
      const response = await fetch(
        `/v1/operator/sessions/${session.id}/commands`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${getToken()}`,
            "content-type": "application/json",
          },
          body: JSON.stringify({ text }),
        },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const message =
          body?.error?.message ||
          body?.error?.code ||
          `Command failed (HTTP ${response.status})`;
        addStreamError(`Command not accepted: ${message}`);
        return;
      }
      // The input.received / transcript.final events arrive over SSE.
    } catch {
      addStreamError(
        "Command not sent — connection unavailable. Reconnecting…",
      );
    }
  }

  // ── Existing M11 telemetry renderer (unchanged behavior) ───────────────────
  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    seedPoints(rect.width, rect.height);
  }

  function insideHead(x, y) {
    const skull = ((x + 0.08) / 0.58) ** 2 + ((y + 0.12) / 0.72) ** 2 < 1;
    const face = ((x - 0.38) / 0.34) ** 2 + ((y + 0.03) / 0.52) ** 2 < 1;
    const neck =
      x > -0.55 &&
      x < -0.05 &&
      y > 0.35 &&
      y < 1.0 &&
      x + 0.28 > (y - 0.86) * 0.33;
    const jawCut = y > 0.3 && x > 0.12 && x < 0.58 && y > 0.92 - x * 0.8;
    const rearCut = x < -0.42 && y > 0.33 && y < 0.83;
    return (skull || face || neck) && !jawCut && !rearCut;
  }

  function seedPoints(width, height) {
    const count = Math.round(
      Math.min(4200, Math.max(1700, (width * height) / 175)),
    );
    const next = [];
    for (let i = 0; i < count; i += 1) {
      let x;
      let y;
      let tries = 0;
      do {
        x = Math.random() * 2 - 1;
        y = Math.random() * 2 - 1;
        tries += 1;
      } while (!insideHead(x, y) && tries < 100);
      if (tries >= 100) continue;
      next.push({
        x,
        y,
        z: Math.random(),
        phase: Math.random() * Math.PI * 2,
        size: 0.35 + Math.random() * 1.65,
      });
    }
    points = next;
  }

  function paletteForPoint(p) {
    const activity = (Math.sin(p.phase + frame * 0.012) + 1) / 2;
    const tone = session.state
      ? orbPresentationForState(session.state).tone
      : "idle";
    if (tone === "danger") {
      return `rgba(255,107,107,${0.14 + activity * 0.7})`;
    }
    if (tone === "attention") {
      return `rgba(255,209,102,${0.14 + activity * 0.7})`;
    }
    if (p.x > 0.05 && p.y < 0.18 && p.y > -0.45 && p.z > 0.5) {
      return `rgba(227,196,134,${0.18 + activity * 0.72})`;
    }
    return `rgba(55,203,255,${0.13 + activity * 0.76})`;
  }

  function render() {
    const rect = canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    ctx.fillStyle = "#03070c";
    ctx.fillRect(0, 0, width, height);

    const cx = width * 0.44;
    const cy = height * 0.49;
    const scale = Math.min(width * 0.37, height * 0.43);
    const load = state?.neural?.load || 0;
    const confidence = state?.neural?.confidence || 0;

    for (const p of points) {
      const wobble = Math.sin(frame * 0.01 + p.phase) * (0.6 + load * 0.012);
      const perspective = 0.84 + p.z * 0.24;
      const px = cx + p.x * scale * perspective + wobble;
      const py = cy + p.y * scale + Math.cos(frame * 0.008 + p.phase) * 0.45;
      ctx.beginPath();
      ctx.fillStyle = paletteForPoint(p);
      ctx.arc(px, py, p.size * (0.65 + p.z * 0.5), 0, Math.PI * 2);
      ctx.fill();
    }

    const coreX = cx + scale * 0.2;
    const coreY = cy - scale * 0.12;
    const core = ctx.createRadialGradient(coreX, coreY, 1, coreX, coreY, 48);
    core.addColorStop(0, `rgba(246,220,162,${0.45 + confidence / 200})`);
    core.addColorStop(0.18, "rgba(78,211,255,.35)");
    core.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = core;
    ctx.fillRect(coreX - 50, coreY - 50, 100, 100);

    const baseX = cx - scale * 0.05;
    const baseY = cy + scale * 0.79;
    const glow = ctx.createRadialGradient(baseX, baseY, 0, baseX, baseY, 58);
    glow.addColorStop(0, "rgba(95,226,255,.98)");
    glow.addColorStop(0.18, "rgba(0,169,236,.62)");
    glow.addColorStop(1, "rgba(0,169,236,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(baseX - 60, baseY - 60, 120, 120);

    ctx.lineWidth = 1;
    for (let r = 0; r < 5; r += 1) {
      ctx.beginPath();
      ctx.strokeStyle = `rgba(66,204,255,${0.24 - r * 0.035})`;
      ctx.arc(
        cx - scale * 0.42,
        cy + scale * 0.48,
        38 + r * 17 + Math.sin(frame * 0.02 + r) * 3,
        Math.PI * 1.08,
        Math.PI * 1.78,
      );
      ctx.stroke();
    }

    frame += 1;
    requestAnimationFrame(render);
  }

  function fmtUptime(seconds) {
    const s = Number(seconds) || 0;
    const days = Math.floor(s / 86400);
    const hours = Math.floor((s % 86400) / 3600);
    const minutes = Math.floor((s % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function renderState(data) {
    state = data;
    setText(
      "identity-state",
      `${data.identity.state} / ${data.identity.product}`,
    );
    setText("mode", data.identity.mode);
    setText("focus", `FOCUS: ${data.neural.focus}`);
    setText("confidence", `${data.neural.confidence}%`);
    setText("load", `${data.neural.load}%`);
    setText("alert", data.neural.alertLevel.toUpperCase());
    setText("queued", data.factory.queued);
    setText("pending", data.factory.pending);
    setText("approval", data.factory.awaitingApproval);
    setText("schedules", data.factory.enabledSchedules);
    setText("published", data.factory.publishedRecent);
    setText("failed", data.factory.failedRecent);
    setText("runtime-node", data.runtime.node);
    setText("runtime-uptime", fmtUptime(data.runtime.uptimeSeconds));
    setText(
      "runtime-scheduler",
      data.runtime.scheduler?.running === false ? "PAUSED" : "ACTIVE",
    );
    setText("updated", new Date(data.generatedAt).toLocaleTimeString());

    const list = document.getElementById("module-list");
    list.innerHTML = data.modules
      .map(
        (module) => `
      <div class="module">
        <span class="module-id">${module.id}</span>
        <span class="module-name">${module.name}</span>
        <span class="module-state ${module.state}">${module.state}</span>
      </div>
    `,
      )
      .join("");
  }

  async function refreshState() {
    const token = getToken();
    if (!token) {
      setConnection("AUTH REQUIRED", "offline");
      return;
    }
    try {
      const response = await fetch("/v1/zarvis/state", {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      if (response.status === 401) throw new Error("Session expired");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      renderState(payload.data);
    } catch (error) {
      setText("identity-state", error.message.toUpperCase());
    }
  }

  // ── Init ────────────────────────────────────────────────────────────────────
  window.addEventListener("resize", resize, { passive: true });
  resize();
  render();
  refreshState();
  window.setInterval(refreshState, 3000);

  const sendButton = document.getElementById("command-send");
  const input = document.getElementById("command-input");
  if (sendButton) sendButton.addEventListener("click", submitCommand);
  if (input) {
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") submitCommand();
    });
  }

  loadStoredStream();
  renderStreamEntries();
  renderOrbState();
  createSession();
})();
