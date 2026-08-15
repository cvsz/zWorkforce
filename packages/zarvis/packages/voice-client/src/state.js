/**
 * Canonical conversation state reducer for ZarvisVoiceClient.
 *
 * Immutable reducer pattern. No side effects, no network calls.
 * @module @z-platform/zarvis-voice-client/state
 */

"use strict";

export const INITIAL_STATE = Object.freeze({
  session: "disconnected",  // ZarvisSessionClient state
  ptt: "idle",              // "idle" | "active" | "committed"
  transcript: null,         // string | null
  reply: null,              // string | null
  approvalRequired: false,
  error: null,              // string | null
  lastUpdated: null,        // ISO-8601 timestamp
});

/**
 * Pure reducer. Takes current state and an action, returns next state.
 *
 * @param {object} state - Current state (treat as immutable).
 * @param {{ type: string, payload?: any }} action
 * @returns {object} Next state.
 */
export function reduce(state, action) {
  const now = new Date().toISOString();
  switch (action.type) {
    case "SESSION_STATE":
      return { ...state, session: action.payload, lastUpdated: now };
    case "PTT_START":
      return { ...state, ptt: "active", transcript: null, reply: null, approvalRequired: false, error: null, lastUpdated: now };
    case "PTT_COMMIT":
      return { ...state, ptt: "committed", lastUpdated: now };
    case "PTT_CANCEL":
      return { ...state, ptt: "idle", lastUpdated: now };
    case "TRANSCRIPT":
      return { ...state, transcript: String(action.payload ?? ""), lastUpdated: now };
    case "REPLY":
      return { ...state, reply: String(action.payload ?? ""), ptt: "idle", lastUpdated: now };
    case "APPROVAL_REQUIRED":
      return { ...state, approvalRequired: true, lastUpdated: now };
    case "APPROVAL_RESOLVED":
      return { ...state, approvalRequired: false, lastUpdated: now };
    case "ERROR":
      return { ...state, error: String(action.payload ?? "unknown error"), lastUpdated: now };
    case "RESET":
      return { ...INITIAL_STATE, lastUpdated: now };
    default:
      return state;
  }
}

/**
 * Simple store wrapping the reducer with subscribe/dispatch.
 */
export class VoiceStore {
  constructor(initialState = INITIAL_STATE) {
    this._state = { ...initialState };
    this._listeners = new Set();
  }

  get state() { return this._state; }

  dispatch(action) {
    const next = reduce(this._state, action);
    if (next !== this._state) {
      this._state = next;
      this._listeners.forEach((fn) => fn(next));
    }
  }

  subscribe(fn) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  }
}
