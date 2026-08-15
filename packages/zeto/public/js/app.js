/**
 * Zeto application dashboard
 * Pages: Dashboard, Compose, Queue, Scheduler, Feed, History, Settings
 */
(function () {
  "use strict";

  // ── Router ──────────────────────────────────────────────────────────────────
  const pages = {
    dashboard: { el: null, onEnter: loadDashboard },
    "control-room": { el: null, onEnter: loadControlRoom },
    compose: { el: null, onEnter: initComposePage },
    queue: { el: null, onEnter: loadQueue },
    scheduler: { el: null, onEnter: loadScheduler },
    feed: { el: null, onEnter: loadFeed },
    history: { el: null, onEnter: loadHistory },
    settings: { el: null, onEnter: loadSettings },
  };

  let currentPage = "dashboard";
  let currentPageId = "default";
  let userRole = "viewer";

  function navigate(pageId) {
    if (!pages[pageId]) return;
    document
      .querySelectorAll(".page")
      .forEach((p) => p.classList.remove("active"));
    document.querySelectorAll(".nav-link").forEach((l) => {
      l.classList.toggle("active", l.dataset.page === pageId);
    });

    const el = document.getElementById(`page-${pageId}`);
    if (el) el.classList.add("active");
    currentPage = pageId;

    closeSidebar();
    if (pages[pageId].onEnter) pages[pageId].onEnter();
  }

  document.querySelectorAll(".nav-link[data-page]").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      navigate(link.dataset.page);
    });
  });

  document.querySelectorAll("[data-page]").forEach((el) => {
    if (!el.classList.contains("nav-link") && el.tagName === "A") {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        navigate(el.dataset.page);
      });
    }
  });

  // ── Sidebar Toggle ───────────────────────────────────────────────────────────
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("overlay");

  document.getElementById("sidebar-open")?.addEventListener("click", () => {
    sidebar.classList.add("open");
    overlay.classList.add("active");
  });

  document
    .getElementById("sidebar-close")
    ?.addEventListener("click", closeSidebar);
  overlay.addEventListener("click", closeSidebar);

  function closeSidebar() {
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
  }

  // ── Toast ────────────────────────────────────────────────────────────────────
  function toast(msg, type = "success", durationMs = 4500) {
    const container = document.getElementById("toast-container");
    const el = document.createElement("div");
    el.className = `toast ${type}`;

    const icons = {
      success:
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
      error:
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
      warning:
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    };

    el.innerHTML = `${icons[type] || ""}<span>${msg}</span>`;
    container.appendChild(el);

    setTimeout(() => {
      el.style.animation = "slideOut 0.3s ease forwards";
      setTimeout(() => el.remove(), 300);
    }, durationMs);
  }

  // ── API Helper ───────────────────────────────────────────────────────────────
  async function api(method, path, body = null, isFormData = false) {
    const opts = { method, headers: {} };
    if (currentPageId) {
      opts.headers["x-page-id"] = currentPageId;
    }
    const token = localStorage.getItem("zeto_token");
    if (token) {
      opts.headers["Authorization"] = `Bearer ${token}`;
    }
    if (body && !isFormData) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    } else if (body && isFormData) {
      opts.body = body; // FormData — let browser set Content-Type
    }
    const res = await fetch(path, opts);

    if (res.status === 401 && path !== "/api/auth/login") {
      logoutLocal();
      throw new Error("Session expired. Please log in again.");
    }

    const json = await res.json();
    if (!json.ok && !res.ok)
      throw new Error(json.error?.message || "Request failed");
    return json;
  }

  // ── Health Check ─────────────────────────────────────────────────────────────
  async function checkHealth() {
    const badge = document.getElementById("system-status");
    const text = document.getElementById("status-text");

    try {
      await api("GET", "/health");
      if (text) text.textContent = "Online";
      badge?.classList.remove("offline");
    } catch {
      if (text) text.textContent = "Offline";
      badge?.classList.add("offline");
    }
  }

  // ── Format helpers ────────────────────────────────────────────────────────────
  function fmtDate(d) {
    if (!d) return "--";
    return new Date(d).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function fmtRelative(d) {
    if (!d) return "--";
    const diff = Date.now() - new Date(d).getTime();
    const min = Math.floor(diff / 60000);
    if (min < 1) return "Just now";
    if (min < 60) return `${min}m ago`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}h ago`;
    return `${Math.floor(hr / 24)}d ago`;
  }

  function escHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // ── Set loading state ─────────────────────────────────────────────────────────
  function setLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    btn.classList.toggle("loading", loading);
  }

  // ══════════════════════════════════════════════════════════════════
  //  PAGE: DASHBOARD
  // ══════════════════════════════════════════════════════════════════
  async function loadDashboard() {
    await Promise.all([
      loadDashboardInsights(),
      loadDashboardQueue(),
      loadMiniHistory(),
      loadPendingApprovals(),
    ]);
  }

  async function loadDashboardInsights() {
    try {
      const [configData, insightsData, schedulesData] = await Promise.all([
        api("GET", "/api/facebook/config"),
        api("GET", "/api/facebook/insights"),
        api("GET", "/api/schedules"),
      ]);

      // Followers
      const followers =
        insightsData.data?.followers_count ??
        insightsData.data?.fan_count ??
        "--";
      setText("kpi-followers", formatNum(followers));

      // Page connection badge
      const badge = document.getElementById("page-connection-badge");
      const pageInfo = document.getElementById("page-info");
      const pageName =
        insightsData.data?.name || configData.data?.pageId || "Not Connected";

      if (
        configData.data?.hasAccessToken &&
        insightsData.configured !== false
      ) {
        if (badge) {
          badge.textContent = "Connected";
          badge.className = "badge badge-green";
        }
        if (pageInfo) {
          pageInfo.innerHTML = `
            <div class="page-info-name">${escHtml(pageName)}</div>
            <div class="page-info-sub">Page ID: ${escHtml(configData.data.pageId || "--")}</div>
            <div class="page-info-sub">Fans: ${formatNum(insightsData.data?.fan_count ?? "--")}</div>
          `;
        }
        // Update compose preview page name
        const previewPageName = document.getElementById("preview-page-name");
        if (previewPageName) previewPageName.textContent = pageName;
      } else {
        if (badge) {
          badge.textContent = "Not Connected";
          badge.className = "badge badge-red";
        }
        if (pageInfo)
          pageInfo.innerHTML = `<div class="page-info-sub text-muted">Set FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN in .env</div>`;
      }

      // Queue size
      setText("kpi-queue-size", configData.data?.queueLength ?? "--");

      // Active schedules (custom)
      setText("kpi-schedules", schedulesData.data?.length ?? "--");

      // Update queue badge
      const qb = document.getElementById("queue-badge");
      const pending = configData.data?.pendingCount ?? 0;
      if (qb) {
        qb.style.display = pending > 0 ? "inline-flex" : "none";
        qb.textContent = pending;
      }
      setText("queue-count-badge", configData.data?.queueLength ?? 0);
    } catch (e) {
      console.error("Dashboard insights error:", e);
    }
  }

  async function loadDashboardQueue() {
    try {
      const data = await api("GET", "/api/history");
      const history = data.data || [];
      const today = new Date().toDateString();
      const todayPosts = history.filter(
        (h) =>
          h.status === "success" &&
          new Date(h.createdAt).toDateString() === today,
      );
      setText("kpi-posts-today", todayPosts.length);
    } catch {
      setText("kpi-posts-today", "--");
    }
  }

  async function loadMiniHistory() {
    const el = document.getElementById("mini-history-list");
    if (!el) return;
    try {
      const data = await api("GET", "/api/history?limit=4");
      const items = data.data || [];
      if (items.length === 0) {
        el.innerHTML =
          '<div class="text-muted small" style="padding:8px 0;">No activity yet.</div>';
        return;
      }
      el.innerHTML = items
        .map(
          (h) => `
        <div class="mini-history-item">
          <span class="badge ${h.status === "success" ? "badge-green" : "badge-red"}">${h.status}</span>
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:0.82rem;">${escHtml(h.message || h.type || "--")}</span>
          <span class="text-muted" style="font-size:0.72rem;white-space:nowrap;">${fmtRelative(h.createdAt)}</span>
        </div>
      `,
        )
        .join("");
    } catch {
      el.innerHTML =
        '<div class="text-muted small" style="padding:8px 0;">Failed to load.</div>';
    }
  }

  async function loadPendingApprovals() {
    const el = document.getElementById("pending-approvals-list");
    if (!el) return;
    try {
      const data = await api("GET", "/api/queue/pending-review");
      const items = data.data || [];
      if (items.length === 0) {
        el.innerHTML =
          '<div class="text-muted small" style="padding:16px 0;text-align:center;">No pending reviews. All clean! ✨</div>';
        return;
      }
      el.innerHTML = items
        .map(
          (item) => `
        <div class="pending-approval-item" id="pa-${item.id}" style="border-bottom:1px solid rgba(255,255,255,0.08);padding:12px 0;">
          <div style="margin-bottom:8px;">
            <textarea class="edit-pending-message" id="pa-msg-${item.id}" rows="3" style="width:100%;font-size:0.85rem;line-height:1.4;background:rgba(0,0,0,0.2);color:#fff;border:1px solid rgba(255,255,255,0.1);border-radius:4px;padding:6px;">${escHtml(item.message)}</textarea>
          </div>
          <div class="meta-row" style="display:flex;justify-content:space-between;align-items:center;font-size:0.75rem;color:var(--text-muted);">
            <span>${fmtDate(item.createdAt)} ${item.imageUrl ? "🖼️ photo" : ""}</span>
            <div style="display:flex;gap:6px;">
              <button class="btn btn-primary btn-sm" onclick="approvePending('${item.id}')">Approve</button>
              <button class="btn btn-danger btn-sm" onclick="rejectPending('${item.id}')">Reject</button>
            </div>
          </div>
        </div>
      `,
        )
        .join("");
    } catch {
      el.innerHTML =
        '<div class="text-muted small" style="padding:16px 0;text-align:center;">Failed to load pending approvals.</div>';
    }
  }

  window.approvePending = async (id) => {
    const msgArea = document.getElementById(`pa-msg-${id}`);
    const message = msgArea ? msgArea.value.trim() : "";
    try {
      await api("POST", `/api/queue/${id}/approve`, { message });
      toast("Approved and queued! ✅");
      loadDashboard();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  window.rejectPending = async (id) => {
    try {
      await api("DELETE", `/api/queue/${id}`);
      toast("Rejected/Deleted successfully");
      loadDashboard();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function formatNum(n) {
    if (n === "--" || n === null || n === undefined) return "--";
    return Number(n).toLocaleString();
  }

  // Quick post on dashboard
  const quickPostForm = document.getElementById("quick-post-form");
  if (quickPostForm) {
    const btnQuickPost = document.getElementById("btn-quick-post");
    const btnQuickQueue = document.getElementById("btn-quick-queue");
    const quickMsg = document.getElementById("quick-message");

    quickPostForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = quickMsg.value.trim();
      if (!msg) return toast("Message is required", "error");
      setLoading(btnQuickPost, true);
      try {
        await api("POST", "/api/facebook/post-message", { message: msg });
        toast("Published to Facebook! ✅");
        quickMsg.value = "";
        loadDashboard();
      } catch (err) {
        toast(err.message, "error");
      } finally {
        setLoading(btnQuickPost, false);
      }
    });

    btnQuickQueue?.addEventListener("click", async () => {
      const msg = quickMsg.value.trim();
      if (!msg) return toast("Message is required", "error");
      setLoading(btnQuickQueue, true);
      try {
        await api("POST", "/api/queue", { message: msg });
        toast("Added to queue!");
        quickMsg.value = "";
        loadDashboard();
      } catch (err) {
        toast(err.message, "error");
      } finally {
        setLoading(btnQuickQueue, false);
      }
    });
  }

  document
    .getElementById("btn-refresh-all")
    ?.addEventListener("click", loadDashboard);
  document
    .getElementById("btn-refresh-approvals")
    ?.addEventListener("click", loadPendingApprovals);

  async function loadControlRoom() {
    const brandSelect = document.getElementById("control-brand-select");
    const runsContainer = document.getElementById("control-runs");
    const providersContainer = document.getElementById("control-providers");
    try {
      const [brandsResponse, providersResponse] = await Promise.all([
        api("GET", "/v1/brands?limit=100"),
        api("GET", "/v1/providers"),
      ]);
      const brands = brandsResponse.data || [];
      if (!brands.length) {
        runsContainer.innerHTML =
          '<div class="empty-state"><p>No persisted brands are available.</p></div>';
        return;
      }
      const selected = brandSelect.value || brands[0].id;
      brandSelect.innerHTML = brands
        .map(
          (brand) =>
            `<option value="${escHtml(brand.id)}" ${brand.id === selected ? "selected" : ""}>${escHtml(brand.name)}</option>`,
        )
        .join("");
      renderControlProviders(providersResponse.data || []);
      await loadControlBrand(brandSelect.value);
      document.getElementById("control-updated").textContent =
        `Updated ${new Date().toLocaleTimeString()}`;
    } catch (error) {
      runsContainer.innerHTML = `<div class="empty-state"><p>${escHtml(error.message)}</p></div>`;
      providersContainer.innerHTML =
        '<div class="text-muted small">Provider inventory unavailable.</div>';
    }
  }

  async function loadControlBrand(brandId) {
    const [analyticsResponse, runsResponse] = await Promise.all([
      api(
        "GET",
        `/v1/analytics/control-room?brandId=${encodeURIComponent(brandId)}&days=30`,
      ),
      api(
        "GET",
        `/v1/workflow-runs?brandId=${encodeURIComponent(brandId)}&limit=25`,
      ),
    ]);
    const report = analyticsResponse.data;
    const runs = runsResponse.data || [];
    setText("control-reach", formatNum(report.kpis.reach.current));
    setText("control-engagement", formatNum(report.kpis.engagement.current));
    setText("control-reach-delta", controlDelta(report.kpis.reach));
    setText("control-engagement-delta", controlDelta(report.kpis.engagement));
    setText("control-run-count", runs.length);
    const succeeded = runs.filter((run) => run.status === "succeeded").length;
    setText("control-run-detail", `${succeeded} completed`);
    setText(
      "control-cost",
      `$${runs.reduce((sum, run) => sum + Number(run.cost || 0), 0).toFixed(2)}`,
    );
    const blocked = runs.filter((run) => Number(run.blocked_steps) > 0);
    setText("control-approval-count", `${blocked.length} awaiting approval`);
    renderControlRuns(runs);
  }

  function controlDelta(metric) {
    if (metric.deltaPercent == null) return "No prior-period baseline";
    const sign = metric.deltaPercent > 0 ? "+" : "";
    return `${sign}${metric.deltaPercent.toFixed(1)}% vs prior period`;
  }

  function renderControlRuns(runs) {
    const container = document.getElementById("control-runs");
    if (!runs.length) {
      container.innerHTML =
        '<div class="empty-state"><p>No workflow runs for this brand.</p></div>';
      return;
    }
    container.innerHTML = runs
      .map((run) => {
        const blocked = Number(run.blocked_steps) > 0;
        const progress = `${run.succeeded_steps}/${run.step_count}`;
        return `<div class="control-row">
          <div class="control-row-main">
            <div class="control-row-title">${escHtml(run.workflow_name)}</div>
            <div class="control-row-meta"><code>${escHtml(run.trace_id?.slice(0, 16))}</code><span>${fmtDate(run.created_at)}</span><span>${progress} steps</span></div>
          </div>
          <div class="control-row-actions">
            <span class="badge ${blocked ? "badge-yellow" : run.status === "succeeded" ? "badge-green" : run.status === "failed" ? "badge-red" : "badge-blue"}">${blocked ? "approval" : escHtml(run.status)}</span>
            ${blocked && userRole !== "viewer" ? `<button class="btn btn-primary btn-sm" onclick="approveFactoryRun('${run.id}')">Approve</button>` : ""}
          </div>
        </div>`;
      })
      .join("");
  }

  function renderControlProviders(providers) {
    const container = document.getElementById("control-providers");
    container.innerHTML = providers
      .map((provider) => {
        const capabilities = Object.entries(provider.capabilities)
          .filter(([, enabled]) => enabled)
          .map(([name]) => `<span class="capability">${escHtml(name)}</span>`)
          .join("");
        return `<div class="control-row"><div class="control-row-main"><div class="control-row-title">${escHtml(provider.name)}</div><div class="capability-list">${capabilities}</div></div><span class="status-indicator" title="Adapter registered"></span></div>`;
      })
      .join("");
  }

  window.approveFactoryRun = async (runId) => {
    try {
      await api("POST", `/v1/factory-runs/${runId}/approve`, {
        decision: "approved",
      });
      toast("Factory run approved and resumed");
      await loadControlRoom();
    } catch (error) {
      toast(error.message, "error");
    }
  };

  document
    .getElementById("btn-refresh-control-room")
    ?.addEventListener("click", loadControlRoom);
  document
    .getElementById("control-brand-select")
    ?.addEventListener("change", (event) =>
      loadControlBrand(event.target.value),
    );

  // ══════════════════════════════════════════════════════════════════
  //  PAGE: COMPOSE
  // ══════════════════════════════════════════════════════════════════
  function initComposePage() {
    const msgEl = document.getElementById("compose-message");
    const charCount = document.getElementById("char-count");
    const previewTxt = document.getElementById("preview-text");
    const previewImg = document.getElementById("preview-image");
    const imgUrlEl = document.getElementById("compose-image-url");
    const fileEl = document.getElementById("compose-file");
    const dropZone = document.getElementById("file-drop-zone");
    const filePreview = document.getElementById("file-preview");

    // Character counter + preview
    msgEl?.addEventListener("input", () => {
      charCount.textContent = msgEl.value.length;
      previewTxt.textContent = msgEl.value || "";
      if (!msgEl.value)
        previewTxt.innerHTML =
          '<span class="text-muted small">Start typing to preview...</span>';
    });

    // Image URL preview
    imgUrlEl?.addEventListener("input", () => {
      if (imgUrlEl.value) {
        previewImg.innerHTML = `<img src="${escHtml(imgUrlEl.value)}" alt="preview" style="width:100%;max-height:240px;object-fit:cover;">`;
        previewImg.style.display = "block";
      } else {
        previewImg.style.display = "none";
      }
    });

    // Upload tabs
    document.querySelectorAll(".upload-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document
          .querySelectorAll(".upload-tab")
          .forEach((t) => t.classList.remove("active"));
        document
          .querySelectorAll(".upload-panel")
          .forEach((p) => p.classList.remove("active"));
        tab.classList.add("active");
        const panel = document.getElementById(
          `upload-${tab.dataset.tab}-panel`,
        );
        if (panel) panel.classList.add("active");
      });
    });

    // File drop zone
    dropZone?.addEventListener("click", () => fileEl?.click());

    dropZone?.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("dragging");
    });
    dropZone?.addEventListener("dragleave", () =>
      dropZone.classList.remove("dragging"),
    );
    dropZone?.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragging");
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelect(file, fileEl, filePreview, previewImg);
    });

    fileEl?.addEventListener("change", () => {
      const file = fileEl.files[0];
      if (file) handleFileSelect(file, fileEl, filePreview, previewImg);
    });
  }

  function handleFileSelect(file, fileInput, previewContainer, previewImg) {
    if (!file.type.startsWith("image/"))
      return toast("Only images allowed", "error");
    const url = URL.createObjectURL(file);
    previewContainer.innerHTML = `<img src="${url}" alt="${escHtml(file.name)}" style="max-width:100%;max-height:160px;border-radius:6px;margin-top:10px;">`;
    previewContainer.style.display = "block";
    previewImg.innerHTML = `<img src="${url}" alt="preview" style="width:100%;max-height:240px;object-fit:cover;">`;
    previewImg.style.display = "block";
  }

  // Compose form submit
  const composeForm = document.getElementById("compose-form");
  if (composeForm) {
    const btnSubmit = document.getElementById("btn-compose-submit");
    const btnAddQueue = document.getElementById("btn-compose-queue");

    composeForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const message = document.getElementById("compose-message").value.trim();
      const link = document.getElementById("compose-link").value.trim();
      const imageUrl = document
        .getElementById("compose-image-url")
        .value.trim();
      const fileEl = document.getElementById("compose-file");
      const hasFile = fileEl?.files.length > 0;

      if (!message) return toast("Message is required", "error");
      setLoading(btnSubmit, true);

      try {
        if (hasFile) {
          const fd = new FormData();
          fd.append("message", message);
          fd.append("image", fileEl.files[0]);
          await api("POST", "/api/facebook/post-photo", fd, true);
          toast("Photo published to Facebook! 🖼️");
        } else if (imageUrl) {
          await api("POST", "/api/facebook/post-photo", {
            message,
            url: imageUrl,
          });
          toast("Photo published to Facebook! 🖼️");
        } else {
          await api("POST", "/api/facebook/post-message", {
            message,
            link: link || undefined,
          });
          toast("Post published to Facebook! ✅");
        }
        composeForm.reset();
        document.getElementById("char-count").textContent = "0";
        document.getElementById("preview-text").innerHTML =
          '<span class="text-muted small">Start typing to preview...</span>';
        document.getElementById("preview-image").style.display = "none";
        document.getElementById("file-preview").style.display = "none";
      } catch (err) {
        toast(err.message, "error");
      } finally {
        setLoading(btnSubmit, false);
      }
    });

    btnAddQueue?.addEventListener("click", async () => {
      const message = document.getElementById("compose-message").value.trim();
      const imageUrl = document
        .getElementById("compose-image-url")
        .value.trim();
      if (!message) return toast("Message is required", "error");
      setLoading(btnAddQueue, true);
      try {
        await api("POST", "/api/queue", {
          message,
          imageUrl: imageUrl || undefined,
        });
        toast("Added to queue!");
        composeForm.reset();
      } catch (err) {
        toast(err.message, "error");
      } finally {
        setLoading(btnAddQueue, false);
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════
  //  PAGE: QUEUE
  // ══════════════════════════════════════════════════════════════════
  async function loadQueue() {
    const container = document.getElementById("queue-list");
    if (!container) return;
    container.innerHTML =
      '<div class="text-muted" style="padding:32px;text-align:center;">Loading...</div>';
    try {
      const data = await api("GET", "/api/queue");
      const items = data.data || [];
      setText("queue-count-badge", items.length);

      // Update sidebar badge
      const qb = document.getElementById("queue-badge");
      const pending = items.filter((i) => i.status === "pending").length;
      if (qb) {
        qb.style.display = pending > 0 ? "inline-flex" : "none";
        qb.textContent = pending;
      }

      if (items.length === 0) {
        container.innerHTML = `<div class="empty-state"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line></svg><p>Queue is empty.</p></div>`;
        return;
      }

      container.innerHTML = items
        .map((item) => {
          const statusBadge =
            item.status === "published"
              ? "badge-green"
              : item.status === "error"
                ? "badge-red"
                : item.status === "publishing"
                  ? "badge-yellow"
                  : "badge-blue";
          return `
          <div class="queue-item" id="qi-${item.id}">
            <div class="queue-item-body">
              <div class="queue-item-msg">${escHtml(item.message)}</div>
              <div class="queue-item-meta">
                <span>${fmtDate(item.createdAt)}</span>
                ${item.imageUrl ? "<span>🖼️ photo</span>" : ""}
                <span class="badge ${statusBadge}">${item.status}</span>
              </div>
            </div>
            <div class="queue-item-actions">
              ${item.status === "pending" ? `<button class="btn btn-primary btn-sm" onclick="publishQueueItem('${item.id}')">▶ Publish</button>` : ""}
              <button class="btn btn-danger btn-sm" onclick="removeQueueItem('${item.id}')">✕</button>
            </div>
          </div>
        `;
        })
        .join("");
    } catch (err) {
      container.innerHTML = `<div class="text-muted" style="padding:32px;text-align:center;">Failed to load: ${escHtml(err.message)}</div>`;
    }
  }

  window.publishQueueItem = async (id) => {
    try {
      await api("POST", `/api/queue/${id}/publish`);
      toast("Published from queue! ✅");
      loadQueue();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  window.removeQueueItem = async (id) => {
    try {
      await api("DELETE", `/api/queue/${id}`);
      document.getElementById(`qi-${id}`)?.remove();
      toast("Removed from queue");
      loadQueue();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  document
    .getElementById("btn-queue-refresh")
    ?.addEventListener("click", loadQueue);
  document
    .getElementById("btn-queue-clear")
    ?.addEventListener("click", async () => {
      if (!confirm("Clear entire queue?")) return;
      try {
        await api("DELETE", "/api/queue");
        toast("Queue cleared");
        loadQueue();
      } catch (err) {
        toast(err.message, "error");
      }
    });

  // Queue add form
  const queueAddForm = document.getElementById("queue-add-form");
  if (queueAddForm) {
    queueAddForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const message = document.getElementById("queue-message").value.trim();
      const imageUrl = document.getElementById("queue-image-url").value.trim();
      if (!message) return toast("Message is required", "error");
      try {
        await api("POST", "/api/queue", {
          message,
          imageUrl: imageUrl || undefined,
        });
        toast("Added to queue!");
        queueAddForm.reset();
        loadQueue();
      } catch (err) {
        toast(err.message, "error");
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════
  //  PAGE: SCHEDULER
  // ══════════════════════════════════════════════════════════════════
  async function loadScheduler() {
    await Promise.all([loadSchedulerStatus(), loadSchedules()]);
  }

  async function loadSchedulerStatus() {
    try {
      const data = await api("GET", "/health");
      const badge = document.getElementById("scheduler-status-badge");
      const count = data.scheduler?.count ?? 0;
      if (badge) {
        badge.textContent = count > 0 ? `${count} job(s) active` : "No jobs";
        badge.className = `badge ${count > 0 ? "badge-green" : "badge-red"}`;
      }
    } catch {
      // The global health badge remains the source of connectivity status.
    }

    try {
      const data = await api("GET", "/api/settings");
      const cronDisplay = document.getElementById("scheduler-cron-display");
      const cronInput = document.getElementById("scheduler-cron-input");
      if (cronDisplay)
        cronDisplay.textContent = data.data?.defaultCron || "0 * * * *";
      if (cronInput) cronInput.value = data.data?.defaultCron || "0 * * * *";
    } catch {
      // Settings remain unchanged when the API is unavailable.
    }
  }

  async function loadSchedules() {
    const container = document.getElementById("schedules-list");
    if (!container) return;
    try {
      const data = await api("GET", "/api/schedules");
      const items = data.data || [];

      if (items.length === 0) {
        container.innerHTML = `<div class="empty-state"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg><p>No custom schedules.</p></div>`;
        return;
      }

      container.innerHTML = items
        .map(
          (s) => `
        <div class="schedule-item" id="sch-${s.id}">
          <div style="flex-shrink:0;">
            <span class="badge ${s.enabled ? "badge-green" : ""}">${s.enabled ? "On" : "Off"}</span>
          </div>
          <div class="schedule-body">
            <div class="schedule-name">${escHtml(s.name)}</div>
            <div class="schedule-detail">${escHtml(s.cron)}</div>
            <div class="schedule-msg">${escHtml(s.message)}</div>
          </div>
          <div class="schedule-actions">
            <button class="btn btn-ghost btn-sm" onclick="toggleSchedule('${s.id}', ${!s.enabled})">${s.enabled ? "Disable" : "Enable"}</button>
            <button class="btn btn-danger btn-sm" onclick="deleteSchedule('${s.id}')">Delete</button>
          </div>
        </div>
      `,
        )
        .join("");
    } catch (err) {
      container.innerHTML = `<div class="text-muted" style="padding:32px;text-align:center;">Failed: ${escHtml(err.message)}</div>`;
    }
  }

  window.toggleSchedule = async (id, enabled) => {
    try {
      await api("PATCH", `/api/schedules/${id}`, { enabled });
      toast(`Schedule ${enabled ? "enabled" : "disabled"}`);
      loadSchedules();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  window.deleteSchedule = async (id) => {
    if (!confirm("Delete this schedule?")) return;
    try {
      await api("DELETE", `/api/schedules/${id}`);
      toast("Schedule deleted");
      loadSchedules();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  // Default scheduler form
  document
    .getElementById("scheduler-default-form")
    ?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const cron = document.getElementById("scheduler-cron-input").value.trim();
      try {
        await api("POST", "/api/scheduler/restart", { cron });
        await api("PATCH", "/api/settings", { defaultCron: cron });
        toast(`Scheduler restarted with ${cron}`);
        loadSchedulerStatus();
      } catch (err) {
        toast(err.message, "error");
      }
    });

  // Trigger now
  document
    .getElementById("btn-trigger-now")
    ?.addEventListener("click", async () => {
      try {
        await api("POST", "/api/scheduler/trigger");
        toast("Auto-post triggered manually ✅");
      } catch (err) {
        toast(err.message, "error");
      }
    });

  // Add custom schedule
  document
    .getElementById("schedule-add-form")
    ?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("schedule-name").value.trim();
      const cron = document.getElementById("schedule-cron").value.trim();
      const message = document.getElementById("schedule-message").value.trim();
      try {
        await api("POST", "/api/schedules", { name, cron, message });
        toast(`Schedule "${name}" added!`);
        e.target.reset();
        loadSchedules();
      } catch (err) {
        toast(err.message, "error");
      }
    });

  document
    .getElementById("btn-schedules-refresh")
    ?.addEventListener("click", loadSchedules);

  // ══════════════════════════════════════════════════════════════════
  //  PAGE: FEED
  // ══════════════════════════════════════════════════════════════════
  async function loadFeed() {
    const container = document.getElementById("feed-list");
    if (!container) return;
    container.innerHTML =
      '<div class="text-muted" style="padding:48px;text-align:center;">Loading posts...</div>';
    try {
      const data = await api("GET", "/api/facebook/posts?limit=20");
      const posts = data.data?.data || [];

      if (posts.length === 0) {
        container.innerHTML =
          '<div class="empty-state"><p>No posts found.</p></div>';
        return;
      }

      container.innerHTML = posts
        .map((post) => {
          const msg = post.message || post.story || "";
          return `
          <div class="feed-item" id="fi-${post.id}">
            <div class="feed-item-header">
              <span class="feed-item-id">${escHtml(post.id)}</span>
              <span class="feed-item-date">${fmtDate(post.created_time)}</span>
            </div>
            ${msg ? `<div class="feed-item-msg">${escHtml(msg)}</div>` : ""}
            ${post.full_picture ? `<div class="feed-item-image"><img src="${escHtml(post.full_picture)}" alt="post image"></div>` : ""}
            ${post.permalink_url ? `<div><a href="${escHtml(post.permalink_url)}" target="_blank" rel="noopener" class="nav-link-inline">View on Facebook ↗</a></div>` : ""}
            <div class="feed-item-actions">
              <button class="btn btn-danger btn-sm" onclick="deleteFbPost('${post.id}')">Delete from Facebook</button>
            </div>
          </div>
        `;
        })
        .join("");
    } catch (err) {
      container.innerHTML = `<div class="text-muted" style="padding:48px;text-align:center;">
        ${escHtml(err.message)}<br><span class="small">Make sure your credentials are configured.</span>
      </div>`;
    }
  }

  window.deleteFbPost = async (postId) => {
    if (!confirm("Delete this post from Facebook? This cannot be undone."))
      return;
    try {
      await api("DELETE", `/api/facebook/posts/${encodeURIComponent(postId)}`);
      toast("Post deleted from Facebook");
      document.getElementById(`fi-${postId}`)?.remove();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  document
    .getElementById("btn-feed-refresh")
    ?.addEventListener("click", loadFeed);

  // ══════════════════════════════════════════════════════════════════
  //  PAGE: HISTORY
  // ══════════════════════════════════════════════════════════════════
  async function loadHistory() {
    const container = document.getElementById("history-list");
    if (!container) return;
    container.innerHTML =
      '<div class="text-muted" style="padding:48px;text-align:center;">Loading...</div>';
    try {
      const data = await api("GET", "/api/history?limit=100");
      const items = data.data || [];

      if (items.length === 0) {
        container.innerHTML =
          '<div class="empty-state"><p>No history yet.</p></div>';
        return;
      }

      container.innerHTML = items
        .map((h) => {
          const iconClass =
            h.status === "success"
              ? "success"
              : h.type === "auto"
                ? "auto"
                : "error";
          const icon =
            h.status === "success" ? "✓" : h.status === "error" ? "✗" : "⟳";
          return `
          <div class="history-item">
            <div class="history-icon ${iconClass}">${icon}</div>
            <div class="history-body">
              <div class="history-msg">${escHtml(h.message || h.type || "--")}</div>
              <div class="history-meta">
                ${h.postId ? `ID: ${h.postId} · ` : ""}
                ${h.source ? `${h.source} · ` : ""}
                ${fmtDate(h.createdAt)}
              </div>
            </div>
            <div class="history-status">
              <span class="badge ${h.status === "success" ? "badge-green" : "badge-red"}">${h.status}</span>
            </div>
          </div>
        `;
        })
        .join("");
    } catch (err) {
      container.innerHTML = `<div class="text-muted" style="padding:48px;text-align:center;">Failed: ${escHtml(err.message)}</div>`;
    }
  }

  document
    .getElementById("btn-history-refresh")
    ?.addEventListener("click", loadHistory);

  // ══════════════════════════════════════════════════════════════════
  //  PAGE: SETTINGS
  // ══════════════════════════════════════════════════════════════════
  async function loadSettings() {
    try {
      const [settingsData, configData, healthData] = await Promise.all([
        api("GET", "/api/settings"),
        api("GET", "/api/facebook/config"),
        api("GET", "/health"),
      ]);

      const s = settingsData.data || {};
      const c = configData.data || {};

      setVal("setting-template", s.autoPostTemplate || "");
      setVal("setting-cron", s.defaultCron || "");
      setVal("setting-max-queue", s.maxQueueSize || 100);

      const schedulerToggle = document.getElementById(
        "setting-scheduler-enabled",
      );
      if (schedulerToggle) schedulerToggle.checked = !!s.schedulerEnabled;

      // Fill Page ID & Token fields in Settings form if present in DB
      setVal("setting-page-id", s.facebookPageId || "");
      setVal("setting-access-token", s.facebookAccessToken || "");

      // Connection info
      setText("info-page-id", c.pageId || "Not set");
      const tokenBadge = document.getElementById("info-token-badge");
      if (tokenBadge) {
        tokenBadge.textContent = c.hasAccessToken ? "Configured" : "Missing";
        tokenBadge.className = `badge ${c.hasAccessToken ? "badge-green" : "badge-red"}`;
      }
      const schedulerBadge = document.getElementById("info-scheduler-badge");
      const jobCount = healthData.scheduler?.count ?? 0;
      if (schedulerBadge) {
        schedulerBadge.textContent =
          jobCount > 0 ? `${jobCount} job(s)` : "No jobs";
        schedulerBadge.className = `badge ${jobCount > 0 ? "badge-green" : ""}`;
      }
      setText("info-env", healthData.environment || "--");
      loadPagesList();
    } catch (err) {
      toast("Failed to load settings: " + err.message, "error");
    }
  }

  function setVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val;
  }

  document
    .getElementById("settings-form")
    ?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const updates = {
        autoPostTemplate: document.getElementById("setting-template").value,
        defaultCron: document.getElementById("setting-cron").value,
        maxQueueSize:
          parseInt(document.getElementById("setting-max-queue").value, 10) ||
          100,
        schedulerEnabled: document.getElementById("setting-scheduler-enabled")
          .checked,
      };
      try {
        await api("PATCH", "/api/settings", updates);
        toast("Settings saved! ✅");
      } catch (err) {
        toast(err.message, "error");
      }
    });

  // Manual Credentials form handler
  document
    .getElementById("manual-credentials-form")
    ?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const updates = {
        facebookPageId: document.getElementById("setting-page-id").value.trim(),
        facebookAccessToken: document
          .getElementById("setting-access-token")
          .value.trim(),
      };
      try {
        await api("PATCH", "/api/settings", updates);
        toast("Credentials saved to DB settings! ✅");
        loadSettings();
      } catch (err) {
        toast(err.message, "error");
      }
    });

  // Token Exchange form handler
  document
    .getElementById("token-exchange-form")
    ?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btnExchange = document.getElementById("btn-exchange-submit");
      const token = document.getElementById("exchange-user-token").value.trim();
      if (!token) return;
      setLoading(btnExchange, true);
      try {
        const res = await api("POST", "/api/facebook/exchange-token", {
          shortLivedToken: token,
        });
        toast(
          `Successfully exchanged token! Page Name: ${res.data.pageName} 🎉`,
        );
        document.getElementById("exchange-user-token").value = "";
        loadSettings();
      } catch (err) {
        toast(err.message, "error");
      } finally {
        setLoading(btnExchange, false);
      }
    });

  // Manual Force Refresh Token
  document
    .getElementById("btn-manual-refresh")
    ?.addEventListener("click", async () => {
      const btnRefresh = document.getElementById("btn-manual-refresh");
      setLoading(btnRefresh, true);
      try {
        const res = await api("POST", "/api/facebook/refresh-token");
        toast(
          `Page Token Refreshed successfully! Page: ${res.data.pageName} ⟳`,
        );
        loadSettings();
      } catch (err) {
        toast(err.message, "error");
      } finally {
        setLoading(btnRefresh, false);
      }
    });

  // ── Init ─────────────────────────────────────────────────────────────────────
  checkHealth();
  checkAuthAndInit();

  document
    .getElementById("global-page-select")
    ?.addEventListener("change", function () {
      currentPageId = this.value;
      toast(
        `Switched page context to: ${this.options[this.selectedIndex].text}`,
      );
      navigate(currentPage);
    });

  function logoutLocal() {
    localStorage.removeItem("zeto_token");
    localStorage.removeItem("zeto_role");
    const loginScreen = document.getElementById("login-screen");
    if (loginScreen) loginScreen.style.display = "flex";
  }

  async function checkAuthAndInit() {
    const token = localStorage.getItem("zeto_token");
    const loginScreen = document.getElementById("login-screen");

    if (!token) {
      if (loginScreen) loginScreen.style.display = "flex";
      return;
    }

    if (loginScreen) loginScreen.style.display = "none";

    try {
      const res = await api("GET", "/api/auth/me");
      userRole = res.data?.role || "viewer";
      localStorage.setItem("zeto_role", userRole);

      applyRolePrivileges();

      // Load app views
      loadPagesDropdown();
      navigate(currentPage);
    } catch (e) {
      console.error("Auth verification failed:", e);
      logoutLocal();
    }
  }

  function applyRolePrivileges() {
    // Enable all inputs/buttons first to reset states
    document
      .querySelectorAll("input, textarea, select, button")
      .forEach((el) => {
        el.disabled = false;
      });

    const connectForm = document.getElementById("connect-page-form");
    if (connectForm) connectForm.style.display = "block";
    const quickPostForm = document.getElementById("quick-post-form");
    if (quickPostForm) quickPostForm.style.display = "block";
    const settingsForm = document.getElementById("settings-form");
    if (settingsForm) settingsForm.style.display = "block";
    const aiSettingsForm = document.getElementById("ai-settings-form");
    if (aiSettingsForm) aiSettingsForm.style.display = "block";
    const schedulerDefaultForm = document.getElementById(
      "scheduler-default-form",
    );
    if (schedulerDefaultForm) schedulerDefaultForm.style.display = "block";
    const scheduleAddForm = document.getElementById("schedule-add-form");
    if (scheduleAddForm) scheduleAddForm.style.display = "block";
    const composeForm = document.getElementById("compose-form");
    if (composeForm) composeForm.style.display = "block";

    // Show disconnect buttons
    document
      .querySelectorAll("#pages-list button")
      .forEach((b) => (b.style.display = "inline-block"));

    if (userRole === "viewer") {
      document
        .querySelectorAll(
          "input, textarea, select:not(#global-page-select), button:not(#btn-logout)",
        )
        .forEach((el) => {
          if (el.id !== "global-page-select" && el.id !== "btn-logout") {
            el.disabled = true;
          }
        });
      if (connectForm) connectForm.style.display = "none";
      if (quickPostForm) quickPostForm.style.display = "none";
      if (settingsForm) settingsForm.style.display = "none";
      if (aiSettingsForm) aiSettingsForm.style.display = "none";
      if (schedulerDefaultForm) schedulerDefaultForm.style.display = "none";
      if (scheduleAddForm) scheduleAddForm.style.display = "none";
      if (composeForm) composeForm.style.display = "none";

      toast("Logged in as Viewer (Read-only) 👁️", "warning");
    } else if (userRole === "editor") {
      if (connectForm) connectForm.style.display = "none";
      if (settingsForm) settingsForm.style.display = "none";
      if (aiSettingsForm) aiSettingsForm.style.display = "none";
      const manualCredentialsForm = document.getElementById(
        "manual-credentials-form",
      );
      if (manualCredentialsForm) manualCredentialsForm.style.display = "none";
      const tokenExchangeForm = document.getElementById("token-exchange-form");
      if (tokenExchangeForm) tokenExchangeForm.style.display = "none";

      document
        .querySelectorAll("#pages-list button")
        .forEach((b) => (b.style.display = "none"));

      toast("Logged in as Editor ✍️");
    } else {
      toast("Logged in as Administrator 🛡️");
    }
  }

  // Auth Forms Bindings
  document
    .getElementById("login-form")
    ?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("login-username").value.trim();
      const password = document.getElementById("login-password").value;
      try {
        const res = await api("POST", "/api/auth/login", {
          username,
          password,
        });
        localStorage.setItem("zeto_token", res.data.token);
        localStorage.setItem("zeto_role", res.data.user.role);
        toast(`Welcome back, ${res.data.user.username}!`);
        checkAuthAndInit();
      } catch (err) {
        toast(err.message, "error");
      }
    });

  document.getElementById("btn-logout")?.addEventListener("click", async () => {
    try {
      await api("POST", "/api/auth/logout");
    } catch {
      // Local logout must still complete when the server is unavailable.
    }
    logoutLocal();
    toast("Logged out successfully");
  });

  async function loadPagesDropdown() {
    const select = document.getElementById("global-page-select");
    if (!select) return;
    try {
      const data = await api("GET", "/api/pages");
      const pages = data.data || [];
      const oldVal = select.value || "default";
      select.innerHTML =
        '<option value="default">🌐 Primary Page (Default)</option>';
      pages.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `📄 ${p.name || p.facebookPageId}`;
        select.appendChild(opt);
      });
      select.value = oldVal;
    } catch (e) {
      console.error("Failed to load pages dropdown:", e);
    }
  }

  async function loadPagesList() {
    const el = document.getElementById("pages-list");
    if (!el) return;
    try {
      const data = await api("GET", "/api/pages");
      const pages = data.data || [];
      if (pages.length === 0) {
        el.innerHTML =
          '<div class="text-muted small" style="padding:12px 0;text-align:center;">No custom pages connected yet. Using primary credentials.</div>';
        return;
      }
      el.innerHTML = pages
        .map(
          (p) => `
        <div class="page-item" id="page-item-${p.id}" style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.08); padding:8px 0;">
          <div style="flex:1;">
            <div style="font-weight:500; font-size:0.9rem;">${escHtml(p.name)}</div>
            <div class="text-muted" style="font-size:0.75rem;">Page ID: ${escHtml(p.facebookPageId)}</div>
          </div>
          <div>
            <button class="btn btn-danger btn-sm" onclick="disconnectPage('${p.id}')">Disconnect</button>
          </div>
        </div>
      `,
        )
        .join("");
    } catch {
      el.innerHTML =
        '<div class="text-muted small" style="padding:12px 0;">Failed to load pages.</div>';
    }
  }

  window.disconnectPage = async (id) => {
    if (
      !confirm(
        "Disconnect this Facebook Page? All queue items and history for this page will be removed.",
      )
    )
      return;
    try {
      await api("DELETE", `/api/pages/${id}`);
      toast("Page disconnected successfully");
      loadPagesList();
      loadPagesDropdown();
      if (currentPageId === id) {
        currentPageId = "default";
        const select = document.getElementById("global-page-select");
        if (select) select.value = "default";
        navigate(currentPage);
      }
    } catch (err) {
      toast(err.message, "error");
    }
  };

  document
    .getElementById("connect-page-form")
    ?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        name: document.getElementById("connect-page-name").value.trim(),
        facebookPageId: document.getElementById("connect-page-id").value.trim(),
        facebookAccessToken: document
          .getElementById("connect-page-token")
          .value.trim(),
      };
      try {
        await api("POST", "/api/pages", payload);
        toast("Facebook page connected successfully! 🎉");
        e.target.reset();
        loadPagesList();
        loadPagesDropdown();
      } catch (err) {
        toast(err.message, "error");
      }
    });

  // Poll health every 30s
  setInterval(checkHealth, 30000);

  // ══════════════════════════════════════════════════════════════════
  //  PAGE: AI CONTENT GENERATOR
  // ══════════════════════════════════════════════════════════════════

  // State
  let _topics = [];
  let _formats = [];
  let _selectedTopic = null;
  let _selectedFormat = null;
  let _lastGenerated = null;

  const FORMAT_LABELS = {
    tips: "📋 Tips",
    howto: "🚀 How-To",
    fact: "💡 Facts",
    quote: "✨ Quote",
    checklist: "☑️ Checklist",
    story: "📖 Story",
  };
  const PROVIDER_LABELS = {
    auto: "🔄 Auto",
    cloudflare: "☁️ Cloudflare",
    openai: "🟢 OpenAI",
    gemini: "🔵 Gemini",
    local: "📝 Local",
    "local-fallback": "📝 Local",
  };

  async function initAiPage() {
    await Promise.all([loadTopics(), loadAiSettings()]);
  }

  async function loadTopics() {
    try {
      const data = await api("GET", "/api/ai/topics");
      _topics = data.data || [];
      const data2 = await api("GET", "/api/ai/formats");
      _formats = data2.data || [];
      renderTopicChips();
      renderFormatTabs();
      renderTopicLibrary();
      populateTopicSelect();
    } catch (e) {
      console.error("Failed to load topics/formats:", e);
    }
  }

  function renderTopicChips() {
    const grid = document.getElementById("topic-grid");
    if (!grid) return;
    grid.innerHTML = _topics
      .map(
        (t) => `
      <div class="topic-chip" data-tag="${t.tag}" title="${t.en}">
        <span>${t.emoji}</span>${t.th}
      </div>
    `,
      )
      .join("");

    grid.querySelectorAll(".topic-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        grid
          .querySelectorAll(".topic-chip")
          .forEach((c) => c.classList.remove("selected"));
        if (_selectedTopic === chip.dataset.tag) {
          _selectedTopic = null; // deselect
        } else {
          chip.classList.add("selected");
          _selectedTopic = chip.dataset.tag;
        }
      });
    });
  }

  function renderFormatTabs() {
    const container = document.getElementById("format-tabs");
    if (!container) return;
    container.innerHTML = _formats
      .map(
        (f) => `
      <button type="button" class="format-tab" data-format="${f}">${FORMAT_LABELS[f] || f}</button>
    `,
      )
      .join("");

    container.querySelectorAll(".format-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        container
          .querySelectorAll(".format-tab")
          .forEach((t) => t.classList.remove("selected"));
        if (_selectedFormat === tab.dataset.format) {
          _selectedFormat = null;
        } else {
          tab.classList.add("selected");
          _selectedFormat = tab.dataset.format;
        }
      });
    });
  }

  function renderTopicLibrary() {
    const el = document.getElementById("topic-library-list");
    if (!el) return;
    el.innerHTML = _topics
      .map(
        (t) => `
      <div class="topic-library-item" data-tag="${t.tag}">
        <span>${t.emoji}</span>
        <div style="flex:1;">
          <div>${t.th}</div>
          <div class="tag">#${t.tag}</div>
        </div>
      </div>
    `,
      )
      .join("");

    el.querySelectorAll(".topic-library-item").forEach((item) => {
      item.addEventListener("click", () => {
        _selectedTopic = item.dataset.tag;
        // Update chips
        document.querySelectorAll(".topic-chip").forEach((c) => {
          c.classList.toggle("selected", c.dataset.tag === _selectedTopic);
        });
        // Update settings select
        const sel = document.getElementById("ai-setting-topic");
        if (sel) sel.value = _selectedTopic;
      });
    });
  }

  function populateTopicSelect() {
    const sel = document.getElementById("ai-setting-topic");
    if (!sel) return;
    _topics.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t.tag;
      opt.textContent = `${t.emoji} ${t.th}`;
      sel.appendChild(opt);
    });
  }

  // Randomize selection
  document.getElementById("btn-ai-randomize")?.addEventListener("click", () => {
    // Random topic
    const t = _topics[Math.floor(Math.random() * _topics.length)];
    _selectedTopic = t?.tag || null;
    document.querySelectorAll(".topic-chip").forEach((c) => {
      c.classList.toggle("selected", c.dataset.tag === _selectedTopic);
    });
    // Random format
    const f = _formats[Math.floor(Math.random() * _formats.length)];
    _selectedFormat = f || null;
    document.querySelectorAll(".format-tab").forEach((t) => {
      t.classList.toggle("selected", t.dataset.format === _selectedFormat);
    });
  });

  // Generate Preview
  const btnGenerate = document.getElementById("btn-ai-generate");
  btnGenerate?.addEventListener("click", async () => {
    setLoading(btnGenerate, true);
    const previewCard = document.getElementById("ai-preview-card");
    const btnQueue = document.getElementById("btn-ai-add-queue");
    const btnPost = document.getElementById("btn-ai-post-now");

    try {
      const payload = {
        tag: _selectedTopic || undefined,
        format: _selectedFormat || undefined,
        withImage: document.getElementById("ai-with-image")?.checked !== false,
        provider:
          document.getElementById("ai-provider-select")?.value || "auto",
      };

      const data = await api("POST", "/api/ai/generate", payload);
      _lastGenerated = data.data;

      // Show preview card
      if (previewCard) previewCard.style.display = "block";

      // Update preview text
      const previewText = document.getElementById("ai-preview-text");
      if (previewText) {
        previewText.style.whiteSpace = "pre-wrap";
        previewText.textContent = _lastGenerated.message;
      }

      // Editable textarea
      const editArea = document.getElementById("ai-preview-edit");
      if (editArea) {
        editArea.value = _lastGenerated.message;
        // Sync edit to preview
        editArea.oninput = () => {
          if (previewText) previewText.textContent = editArea.value;
          if (_lastGenerated) _lastGenerated.message = editArea.value;
        };
      }

      // Image preview
      const previewImg = document.getElementById("ai-preview-image");
      if (previewImg) {
        if (
          _lastGenerated.imageUrl &&
          !_lastGenerated.imageUrl.startsWith("data:")
        ) {
          previewImg.innerHTML = `<img src="${escHtml(_lastGenerated.imageUrl)}" alt="post image" style="width:100%;max-height:240px;object-fit:cover;" onerror="this.parentElement.style.display='none'">`;
          previewImg.style.display = "block";
        } else {
          previewImg.style.display = "none";
        }
      }

      // Update badges
      const topic = _lastGenerated.topic;
      setText(
        "ai-preview-topic",
        `${topic?.emoji || ""} ${topic?.th || topic?.tag || "--"}`,
      );
      setText(
        "ai-preview-format",
        FORMAT_LABELS[_lastGenerated.format] || _lastGenerated.format,
      );
      setText(
        "ai-preview-provider",
        PROVIDER_LABELS[_lastGenerated.provider] || _lastGenerated.provider,
      );

      // Enable action buttons
      if (btnQueue) btnQueue.disabled = false;
      if (btnPost) btnPost.disabled = false;

      toast(
        `Generated! Topic: ${topic?.th || topic?.tag} | Provider: ${_lastGenerated.provider}`,
      );
    } catch (e) {
      toast("Generation failed: " + e.message, "error");
    } finally {
      setLoading(btnGenerate, false);
    }
  });

  // Add Generated Content to Queue
  document
    .getElementById("btn-ai-add-queue")
    ?.addEventListener("click", async () => {
      if (!_lastGenerated) return;
      try {
        await api("POST", "/api/queue", {
          message: _lastGenerated.message,
          imageUrl:
            _lastGenerated.imageUrl &&
            !_lastGenerated.imageUrl.startsWith("data:")
              ? _lastGenerated.imageUrl
              : undefined,
        });
        toast("Added to queue! 📋");
      } catch (e) {
        toast(e.message, "error");
      }
    });

  // Post Generated Content Now
  const btnPostNow = document.getElementById("btn-ai-post-now");
  btnPostNow?.addEventListener("click", async () => {
    if (!_lastGenerated) return;
    if (!confirm("Post this AI-generated content to Facebook now?")) return;
    setLoading(btnPostNow, true);
    try {
      // Override generated content by posting message directly via compose route
      const postPayload = { message: _lastGenerated.message };
      if (
        _lastGenerated.imageUrl &&
        !_lastGenerated.imageUrl.startsWith("data:")
      ) {
        postPayload.url = _lastGenerated.imageUrl;
        await api("POST", "/api/facebook/post-photo", postPayload);
      } else {
        await api("POST", "/api/facebook/post-message", postPayload);
      }
      toast("AI content posted to Facebook! 🚀");
      _lastGenerated = null;
      document.getElementById("btn-ai-add-queue").disabled = true;
      btnPostNow.disabled = true;
      document.getElementById("ai-preview-card").style.display = "none";
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setLoading(btnPostNow, false);
    }
  });

  // Load AI Settings
  async function loadAiSettings() {
    try {
      const [settingsData, healthData] = await Promise.all([
        api("GET", "/api/ai/settings"),
        api("GET", "/health"),
      ]);
      const s = settingsData.data || {};

      // Update KPI
      const isEnabled = s.enabled !== false;
      const aiJobActive = healthData.scheduler?.aiAutoPosterActive;

      setText(
        "ai-kpi-status",
        isEnabled ? (aiJobActive ? "Active" : "Enabled") : "Disabled",
      );
      setText(
        "ai-kpi-provider",
        PROVIDER_LABELS[s.provider || "auto"] || "Auto",
      );

      const autoposterBadge = document.getElementById("ai-autoposter-status");
      if (autoposterBadge) {
        autoposterBadge.textContent = isEnabled ? "Enabled" : "Disabled";
        autoposterBadge.className = `badge ${isEnabled ? "badge-green" : "badge-red"}`;
      }

      const statusBadge = document.getElementById("ai-status-badge");
      if (statusBadge) {
        statusBadge.textContent = isEnabled ? "🤖 Running" : "⏸ Paused";
        statusBadge.className = `badge ${isEnabled ? "badge-green" : ""}`;
      }

      // Fill form
      const topicSel = document.getElementById("ai-setting-topic");
      if (topicSel) topicSel.value = s.topicTag || "";

      const fmtSel = document.getElementById("ai-setting-format");
      if (fmtSel) fmtSel.value = s.postFormat || "";

      const provSel = document.getElementById("ai-setting-provider");
      if (provSel) provSel.value = s.provider || "auto";

      const imgToggle = document.getElementById("ai-setting-image");
      if (imgToggle) imgToggle.checked = s.withImage !== false;

      const approvalToggle = document.getElementById("ai-setting-approval");
      if (approvalToggle) approvalToggle.checked = s.requireApproval !== false;

      const enableToggle = document.getElementById("ai-setting-enabled");
      if (enableToggle) enableToggle.checked = s.enabled !== false;
    } catch (e) {
      console.error("AI settings load error:", e);
    }
  }

  // Save AI Settings
  document
    .getElementById("ai-settings-form")
    ?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const updates = {
        enabled: document.getElementById("ai-setting-enabled")?.checked,
        topicTag:
          document.getElementById("ai-setting-topic")?.value || undefined,
        postFormat:
          document.getElementById("ai-setting-format")?.value || undefined,
        provider:
          document.getElementById("ai-setting-provider")?.value || "auto",
        withImage:
          document.getElementById("ai-setting-image")?.checked !== false,
        requireApproval:
          document.getElementById("ai-setting-approval")?.checked !== false,
      };
      try {
        await api("PATCH", "/api/ai/settings", updates);
        toast("AI auto-poster settings saved! ✅");
        loadAiSettings();
      } catch (err) {
        toast(err.message, "error");
      }
    });

  // Register page
  pages.ai = { el: document.getElementById("page-ai"), onEnter: initAiPage };

  // ── Analytics Page ───────────────────────────────────────────────────────────

  /** Singleton Chart.js instance for the insights line chart */
  let insightsChartInstance = null;

  /**
   * Render (or update) the 30-day insights line chart.
   * @param {{ labels: string[], impressions: number[], engagedUsers: number[], postEngagements: number[] }} data
   */
  function renderInsightsCharts(data) {
    const ctx = document.getElementById("analytics-insights-chart");
    if (!ctx) return;

    // Destroy previous chart instance to avoid canvas reuse error
    if (insightsChartInstance) {
      insightsChartInstance.destroy();
      insightsChartInstance = null;
    }

    const chartColors = {
      impressions: {
        border: "rgba(79, 142, 247, 1)",
        fill: "rgba(79, 142, 247, 0.15)",
      },
      engagedUsers: {
        border: "rgba(16, 185, 129, 1)",
        fill: "rgba(16, 185, 129, 0.15)",
      },
      postEngagements: {
        border: "rgba(168, 85, 247, 1)",
        fill: "rgba(168, 85, 247, 0.12)",
      },
    };

    insightsChartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Impressions",
            data: data.impressions,
            borderColor: chartColors.impressions.border,
            backgroundColor: chartColors.impressions.fill,
            tension: 0.4,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 6,
            borderWidth: 2,
          },
          {
            label: "Engaged Users",
            data: data.engagedUsers,
            borderColor: chartColors.engagedUsers.border,
            backgroundColor: chartColors.engagedUsers.fill,
            tension: 0.4,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 6,
            borderWidth: 2,
          },
          {
            label: "Post Engagements",
            data: data.postEngagements,
            borderColor: chartColors.postEngagements.border,
            backgroundColor: chartColors.postEngagements.fill,
            tension: 0.4,
            fill: false,
            pointRadius: 3,
            pointHoverRadius: 6,
            borderWidth: 2,
            borderDash: [5, 3],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            position: "top",
            labels: {
              color: "rgba(255,255,255,0.75)",
              font: { family: "Outfit, Inter, sans-serif", size: 12 },
              boxWidth: 14,
              padding: 16,
            },
          },
          tooltip: {
            backgroundColor: "rgba(15,20,40,0.92)",
            titleColor: "#fff",
            bodyColor: "rgba(255,255,255,0.8)",
            borderColor: "rgba(255,255,255,0.1)",
            borderWidth: 1,
            padding: 12,
            callbacks: {
              label: (ctx) =>
                ` ${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()}`,
            },
          },
        },
        scales: {
          x: {
            ticks: {
              color: "rgba(255,255,255,0.5)",
              font: { size: 11 },
              maxTicksLimit: 10,
            },
            grid: { color: "rgba(255,255,255,0.05)" },
          },
          y: {
            ticks: {
              color: "rgba(255,255,255,0.5)",
              font: { size: 11 },
              callback: (v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v),
            },
            grid: { color: "rgba(255,255,255,0.07)" },
            beginAtZero: true,
          },
        },
      },
    });
  }

  /**
   * Render the Top 5 Performing Posts leaderboard.
   * @param {Array} posts
   */
  function renderTopPosts(posts) {
    const container = document.getElementById("top-posts-list");
    if (!container) return;

    if (!posts || posts.length === 0) {
      container.innerHTML = `<p class="text-muted small" style="padding:20px 0;text-align:center;">No posts found.</p>`;
      return;
    }

    const medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"];

    container.innerHTML = posts
      .map((post, i) => {
        const preview =
          post.message.length > 120
            ? post.message.slice(0, 117) + "…"
            : post.message;
        const dateStr = post.createdTime
          ? new Date(post.createdTime).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })
          : "";
        const permalink = post.permalink
          ? `<a href="${post.permalink}" target="_blank" rel="noopener" style="color:var(--accent-blue);font-size:0.8rem;text-decoration:none;">View post ↗</a>`
          : "";

        return `
        <div style="display:flex;align-items:flex-start;gap:14px;padding:14px 4px;border-bottom:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:1.6rem;line-height:1;flex-shrink:0;padding-top:2px;">${medals[i]}</div>
          ${post.thumbnail ? `<img src="${post.thumbnail}" alt="thumb" style="width:52px;height:52px;object-fit:cover;border-radius:8px;flex-shrink:0;">` : ""}
          <div style="flex:1;min-width:0;">
            <p style="margin:0 0 6px;font-size:0.88rem;color:rgba(255,255,255,0.85);line-height:1.5;">${preview}</p>
            <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
              <span style="font-size:0.77rem;color:rgba(255,255,255,0.4);">${dateStr}</span>
              <span style="font-size:0.8rem;color:#4f8ef7;">👍 ${post.likes.toLocaleString()}</span>
              <span style="font-size:0.8rem;color:#10b981;">💬 ${post.comments.toLocaleString()}</span>
              <span style="font-size:0.8rem;color:#a855f7;">↗ ${post.shares.toLocaleString()}</span>
              <span style="font-size:0.8rem;font-weight:600;color:#f59e0b;">⭐ ${post.engagement.toLocaleString()} total</span>
              ${permalink}
            </div>
          </div>
        </div>`;
      })
      .join("");
  }

  /** Helper to format numbers with k/M suffix */
  function fmtNum(n) {
    if (!n || isNaN(n)) return "0";
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
    return String(n);
  }

  /** Main loader for the Analytics page */
  async function loadAnalytics() {
    // Reset statuses
    const chartStatus = document.getElementById("analytics-chart-status");
    const topStatus = document.getElementById("top-posts-status");
    if (chartStatus) chartStatus.textContent = "Loading...";
    if (topStatus) topStatus.textContent = "Loading...";

    // Reset KPIs
    [
      "analytics-kpi-impressions",
      "analytics-kpi-engaged",
      "analytics-kpi-post-eng",
      "analytics-kpi-avg-reach",
    ].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.textContent = "--";
    });

    // Fetch history + top posts concurrently
    const [histRes, topRes] = await Promise.allSettled([
      api("GET", "/api/facebook/insights/history?days=30"),
      api("GET", "/api/facebook/posts/top?limit=25"),
    ]);

    // ── Insights history ──
    if (histRes.status === "fulfilled") {
      const body = histRes.value;
      if (body.ok && body.configured && body.data) {
        const d = body.data;
        const totalImpressions = d.impressions.reduce((s, v) => s + v, 0);
        const totalEngaged = d.engagedUsers.reduce((s, v) => s + v, 0);
        const totalPostEng = d.postEngagements.reduce((s, v) => s + v, 0);
        const avgReach =
          d.impressions.length > 0
            ? Math.round(totalImpressions / d.impressions.length)
            : 0;

        const setKpi = (id, val) => {
          const el = document.getElementById(id);
          if (el) el.textContent = fmtNum(val);
        };
        setKpi("analytics-kpi-impressions", totalImpressions);
        setKpi("analytics-kpi-engaged", totalEngaged);
        setKpi("analytics-kpi-post-eng", totalPostEng);
        setKpi("analytics-kpi-avg-reach", avgReach);

        renderInsightsCharts(d);
        if (chartStatus)
          chartStatus.textContent = `Last updated ${new Date().toLocaleTimeString()}`;
      } else if (body.ok && !body.configured) {
        if (chartStatus)
          chartStatus.textContent =
            "Page not connected — configure Facebook credentials in Settings.";
      }
    } else {
      if (chartStatus) chartStatus.textContent = "Failed to load chart data.";
      console.error("[analytics] insights/history error:", histRes.reason);
    }

    // ── Top posts ──
    if (topRes.status === "fulfilled") {
      const body = topRes.value;
      if (body.ok && body.configured) {
        renderTopPosts(body.data || []);
        if (topStatus)
          topStatus.textContent = `${(body.data || []).length} posts ranked`;
      } else if (body.ok && !body.configured) {
        document.getElementById("top-posts-list").innerHTML =
          `<p class="text-muted small" style="padding:20px 0;text-align:center;">Page not connected.</p>`;
        if (topStatus) topStatus.textContent = "";
      }
    } else {
      document.getElementById("top-posts-list").innerHTML =
        `<p class="text-muted small" style="padding:20px 0;text-align:center;">Failed to fetch posts.</p>`;
      if (topStatus) topStatus.textContent = "Error loading";
      console.error("[analytics] top posts error:", topRes.reason);
    }
  }

  // Refresh button
  document
    .getElementById("btn-refresh-analytics")
    ?.addEventListener("click", loadAnalytics);

  // Register Analytics page
  pages.analytics = {
    el: document.getElementById("page-analytics"),
    onEnter: loadAnalytics,
  };
})();
