/**
 * ZarvisVoiceClient — WebSocket/session state machine.
 *
 * Browser-safe. No server credentials. No direct imports of server-side code.
 * @module @z-platform/zarvis-voice-client/client
 */

"use strict";

export const SESSION_STATES = Object.freeze([
  "disconnected",
  "connecting",
  "idle",
  "arming",
  "ready",
  "listening",
  "transcribing",
  "thinking",
  "speaking",
  "approval_required",
  "interrupted",
  "muted",
  "error",
]);

const SESSION_STATE_SET = new Set(SESSION_STATES);

/**
 * @callback OnStateChange
 * @param {string} newState
 * @param {string} previousState
 */

/**
 * @callback OnMessage
 * @param {object} message - Parsed JSON message from the server.
 */

/**
 * Minimal WebSocket session wrapper used by the voice card and ZVoice.
 *
 * Usage:
 *   const client = new ZarvisSessionClient({ url: ticketUrl, onStateChange, onMessage });
 *   client.connect();
 *   // later:
 *   client.disconnect();
 */
export class ZarvisSessionClient extends EventTarget {
  /**
   * @param {object} opts
   * @param {string} opts.url - Short-lived ticket URL (no long-term creds).
   * @param {OnStateChange} [opts.onStateChange]
   * @param {OnMessage} [opts.onMessage]
   * @param {number} [opts.reconnectDelayMs=2000]
   * @param {number} [opts.maxReconnects=3]
   */
  constructor({ url, onStateChange, onMessage, reconnectDelayMs = 2000, maxReconnects = 3 }) {
    super();
    if (!url || typeof url !== "string") throw new TypeError("url must be a non-empty string");
    this._url = url;
    this._onStateChange = onStateChange ?? null;
    this._onMessage = onMessage ?? null;
    this._reconnectDelayMs = reconnectDelayMs;
    this._maxReconnects = maxReconnects;
    this._reconnectCount = 0;
    this._state = "disconnected";
    this._ws = null;
    this._closed = false;
  }

  get state() { return this._state; }

  _setState(next) {
    if (!SESSION_STATE_SET.has(next)) throw new Error(`unknown state: ${next}`);
    const prev = this._state;
    if (prev === next) return;
    this._state = next;
    this._onStateChange?.(next, prev);
    this.dispatchEvent(Object.assign(new Event("statechange"), { state: next, previousState: prev }));
  }

  connect() {
    if (this._closed) throw new Error("client has been permanently closed");
    if (this._ws) return;
    this._setState("connecting");
    const ws = new WebSocket(this._url);
    ws.binaryType = "arraybuffer";
    this._ws = ws;

    ws.addEventListener("open", () => {
      this._reconnectCount = 0;
      this._setState("idle");
    });

    ws.addEventListener("message", (evt) => {
      let msg;
      try {
        msg = JSON.parse(typeof evt.data === "string" ? evt.data : new TextDecoder().decode(evt.data));
      } catch {
        return; // malformed frame — ignore
      }
      const next = msg?.state;
      if (next && SESSION_STATE_SET.has(next)) this._setState(next);
      this._onMessage?.(msg);
      this.dispatchEvent(Object.assign(new Event("message"), { detail: msg }));
    });

    ws.addEventListener("close", (evt) => {
      this._ws = null;
      if (this._closed) { this._setState("disconnected"); return; }
      this._setState("disconnected");
      if (this._reconnectCount < this._maxReconnects) {
        this._reconnectCount += 1;
        setTimeout(() => { if (!this._closed) this.connect(); }, this._reconnectDelayMs);
      } else {
        this._setState("error");
      }
    });

    ws.addEventListener("error", () => {
      // close event always follows; handle state there
    });
  }

  sendJSON(payload) {
    if (!this._ws || this._ws.readyState !== 1 /* OPEN */) return false;
    this._ws.send(JSON.stringify(payload));
    return true;
  }

  sendBinary(bytes) {
    if (!this._ws || this._ws.readyState !== 1) return false;
    this._ws.send(bytes);
    return true;
  }

  /**
   * Permanently close the connection. No further reconnects.
   */
  disconnect() {
    this._closed = true;
    if (this._ws) {
      try { this._ws.close(1000, "client disconnect"); } catch { /* ignore */ }
      this._ws = null;
    }
    this._setState("disconnected");
  }
}
