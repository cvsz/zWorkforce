"use strict";

/**
 * Z.A.R.V.I.S. operator stream — shared pure helpers for the /zarvis command
 * center. Loaded as a browser script (window.OperatorStream) and required by
 * unit tests (module.exports), so the same mapping rules are exercised in both
 * environments.
 *
 * Spec refs: §2.2 S1 (command stream panel), §2.3 (orb states), §2.4 (empty and
 * error states), §4.2 (command stream event shape), §10 (event catalog).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.OperatorStream = factory();
})(typeof self !== "undefined" ? self : this, function () {
  // Max stream entries kept in the UI ring buffer.
  const MAX_ENTRIES = 500;

  /**
   * Parse raw SSE text into { event, data } blocks. Comments (": keep-alive")
   * and empty lines are ignored; multiple data: lines join with "\n".
   */
  function parseSseBlocks(text) {
    const blocks = [];
    const raw = String(text || "").split(/\r?\n\r?\n/);
    for (const chunk of raw) {
      if (!chunk.trim()) continue;
      let event = null;
      const dataLines = [];
      for (const line of chunk.split(/\r?\n/)) {
        if (line.startsWith(":")) continue;
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (dataLines.length) blocks.push({ event, data: dataLines.join("\n") });
    }
    return blocks;
  }

  /** Parse an SSE data payload into a JSON object; null when malformed. */
  function parseEventData(raw) {
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  const TERMINAL_ERROR = ["FAILED", "EMERGENCY_STOPPED"];

  /**
   * Map a catalog event envelope (SSE data payload, payload fields flattened)
   * to a §4.2 command stream entry: { id, session_id, plan_id, step_id, ts,
   * actor, intent, tool, target, risk, approval, result, duration_ms,
   * correlation_id, summary, error? }. Returns null for events that do not
   * belong in the stream (e.g. transcript.partial belongs to the transcript
   * surface).
   */
  function streamEntryFromEvent(event) {
    if (!event || typeof event !== "object") return null;
    const payload = event.payload || event;
    const type = event.type;
    const base = {
      id: event.event_id,
      session_id: event.session_id,
      plan_id: payload.plan_id || null,
      step_id: payload.step_id || null,
      ts: event.occurred_at || null,
      actor: payload.actor || "system",
      intent: payload.intent || null,
      tool: payload.tool || null,
      target: payload.target || null,
      risk: payload.risk || null,
      approval: payload.approval || "not_required",
      result: "ok",
      duration_ms: payload.duration_ms || 0,
      correlation_id: event.correlation_id || null,
      summary: type,
    };

    switch (type) {
      case "session.started":
        return {
          ...base,
          summary: `Session started (${payload.mode || "operator"})`,
        };
      case "session.ended":
        return {
          ...base,
          summary: `Session ended (${payload.to || "terminal"})`,
          result: TERMINAL_ERROR.includes(payload.to) ? "error" : "ok",
        };
      case "session.state_changed":
        return {
          ...base,
          summary: `${payload.from} → ${payload.to}${payload.trigger ? ` (${payload.trigger})` : ""}`,
          result: TERMINAL_ERROR.includes(payload.to)
            ? "error"
            : payload.to === "CANCELLED"
              ? "cancelled"
              : "ok",
        };
      case "input.received":
        return {
          ...base,
          actor: "operator",
          summary: `Command received (${payload.type || "text"})`,
        };
      case "transcript.final":
        return { ...base, actor: "operator", summary: payload.text || "…" };
      case "intent.resolved":
        return {
          ...base,
          actor: "zarvis",
          summary: `Intent: ${payload.intent}${payload.confidence ? ` (${Math.round(payload.confidence * 100)}%)` : ""}`,
        };
      case "plan.created":
        return {
          ...base,
          actor: "zarvis",
          summary: `Plan created (${payload.verdict || "approval_required"})`,
        };
      case "plan.approved":
        return { ...base, actor: "policy", summary: "Plan approved" };
      case "plan.rejected":
        return {
          ...base,
          actor: "policy",
          summary: "Plan rejected",
          result: "cancelled",
        };
      case "step.started":
        return {
          ...base,
          actor: "zarvis",
          summary: `Step ${payload.step_id || "?"} started (${payload.tool || "tool"})`,
        };
      case "step.finished":
        return {
          ...base,
          actor: "zarvis",
          summary: `Step ${payload.step_id || "?"} finished`,
        };
      case "step.failed":
        return {
          ...base,
          actor: "zarvis",
          summary: `Step ${payload.step_id || "?"} failed`,
          result: "error",
          error: payload.error || "step failed",
        };
      case "tool.require_approval":
        return {
          ...base,
          actor: "policy",
          summary: `Approval required for step ${payload.step_id || "?"}`,
          result: "blocked",
          risk: payload.risk || "high",
        };
      case "verification.passed":
        return {
          ...base,
          actor: "zarvis",
          summary: `Verification passed (${payload.step_id || "?"})`,
        };
      case "verification.failed":
        return {
          ...base,
          actor: "zarvis",
          summary: `Verification failed (${payload.step_id || "?"})`,
          result: "error",
          error: "postcondition unmet",
        };
      case "speech.started":
        return { ...base, actor: "zarvis", summary: "Speaking…" };
      case "speech.ended":
        return { ...base, actor: "zarvis", summary: "Speech ended" };
      case "pairing.issued":
        return { ...base, actor: "system", summary: "Pairing token issued" };
      case "pairing.consumed":
        return { ...base, actor: "system", summary: "Pairing token consumed" };
      case "incident.raised":
        return {
          ...base,
          actor: "system",
          summary: `Incident raised (${payload.level || "warning"}${payload.scope ? ` · ${payload.scope}` : ""})`,
          result: "error",
        };
      case "incident.resolved":
        return { ...base, actor: "system", summary: "Incident resolved" };
      case "emergency.stop":
        return {
          ...base,
          actor: "operator",
          summary: `EMERGENCY STOP — ${payload.reason || "safety interrupt"}`,
          result: "error",
          risk: "critical",
          error: payload.reason || "emergency stop",
        };
      default:
        return null;
    }
  }

  /**
   * Orb presentation per spec §2.3. Every canonical operator state maps to a
   * deterministic presentation; reduced-motion fallback is included so the UI
   * never depends on animation to convey state.
   */
  function orbPresentationForState(state) {
    const presentations = {
      IDLE: {
        label: "IDLE",
        tone: "idle",
        motion: "pulse",
        reducedMotion: "Static",
      },
      LISTENING: {
        label: "LISTENING",
        tone: "active",
        motion: "rings",
        reducedMotion: "Listening",
      },
      TRANSCRIBING: {
        label: "TRANSCRIBING",
        tone: "active",
        motion: "tick",
        reducedMotion: "Transcribing",
      },
      THINKING: {
        label: "THINKING",
        tone: "active",
        motion: "orbit",
        reducedMotion: "Thinking",
      },
      PLANNING: {
        label: "PLANNING",
        tone: "active",
        motion: "orbit",
        reducedMotion: "Planning",
      },
      AWAITING_APPROVAL: {
        label: "AWAITING APPROVAL",
        tone: "attention",
        motion: "pulse",
        reducedMotion: "Awaiting approval",
      },
      EXECUTING: {
        label: "EXECUTING",
        tone: "active",
        motion: "directed",
        reducedMotion: "Executing",
      },
      VERIFYING: {
        label: "VERIFYING",
        tone: "active",
        motion: "scan",
        reducedMotion: "Verifying",
      },
      SPEAKING: {
        label: "SPEAKING",
        tone: "active",
        motion: "bars",
        reducedMotion: "Speaking",
      },
      DEGRADED: {
        label: "DEGRADED",
        tone: "attention",
        motion: "tint",
        reducedMotion: "Degraded",
      },
      RECOVERING: {
        label: "RECOVERING",
        tone: "attention",
        motion: "scan",
        reducedMotion: "Recovering",
      },
      REAUTHORIZING: {
        label: "REAUTHORIZING",
        tone: "attention",
        motion: "pulse",
        reducedMotion: "Re-authorizing",
      },
      PAUSED: {
        label: "PAUSED",
        tone: "idle",
        motion: "pulse",
        reducedMotion: "Paused",
      },
      FAILED: {
        label: "FAILED",
        tone: "danger",
        motion: "shake",
        reducedMotion: "Failed",
      },
      CANCELLED: {
        label: "CANCELLED",
        tone: "idle",
        motion: "fade",
        reducedMotion: "Cancelled",
      },
      EMERGENCY_STOPPED: {
        label: "EMERGENCY STOP",
        tone: "danger",
        motion: "flash",
        reducedMotion: "Emergency stopped",
      },
    };
    return (
      presentations[state] || {
        label: state,
        tone: "idle",
        motion: "pulse",
        reducedMotion: state,
      }
    );
  }

  /**
   * Merge new events into an existing ordered list: dedupe by event_id, keep
   * sequence order, cap the buffer. `getSeq` defaults to reading sequence_id.
   */
  function mergeEvents(
    existing = [],
    incoming = [],
    { max = MAX_ENTRIES, getSeq = (e) => e.sequence_id } = {},
  ) {
    const byId = new Map();
    for (const event of existing) byId.set(event.event_id, event);
    for (const event of incoming) {
      if (event && event.event_id) byId.set(event.event_id, event);
    }
    let merged = [...byId.values()];
    merged.sort((a, b) => (getSeq(a) || 0) - (getSeq(b) || 0));
    if (merged.length > max) merged = merged.slice(merged.length - max);
    return merged;
  }

  /** Apply a state_changed event to the current session state, if applicable. */
  function applyStateChanged(currentState, event) {
    if (!event || event.type !== "session.state_changed") return currentState;
    return event.payload?.to || currentState;
  }

  return {
    MAX_ENTRIES,
    parseSseBlocks,
    parseEventData,
    streamEntryFromEvent,
    orbPresentationForState,
    mergeEvents,
    applyStateChanged,
  };
});
