/**
 * Push-to-talk (PTT) controller — presentation-independent.
 *
 * Handles pointer/touch press+release, keyboard (Space hold), and
 * accessible click-toggle fallback. No server credentials, no audio capture.
 * @module @z-platform/zarvis-voice-client/ptt
 */

"use strict";

/**
 * @callback PTTCallback
 * @param {"start"|"commit"|"cancel"} action
 */

/**
 * PTTController wires pointer, keyboard, and accessible fallback events
 * onto a given element and emits `start`, `commit`, and `cancel` actions.
 *
 * Usage:
 *   const ptt = new PTTController(button, { onAction });
 *   ptt.attach();
 *   // later:
 *   ptt.detach();
 */
export class PTTController {
  /**
   * @param {HTMLElement} element
   * @param {object} opts
   * @param {PTTCallback} opts.onAction
   * @param {boolean} [opts.keyboardEnabled=true]
   */
  constructor(element, { onAction, keyboardEnabled = true }) {
    if (!element) throw new TypeError("element is required");
    if (typeof onAction !== "function") throw new TypeError("onAction must be a function");
    this._el = element;
    this._onAction = onAction;
    this._keyboardEnabled = keyboardEnabled;
    this._pointerDown = false;
    this._spaceDown = false;
    this._toggleActive = false;
    this._attached = false;
    // Bound handlers for proper removal.
    this._onPointerDown = this._handlePointerDown.bind(this);
    this._onPointerUp = this._handlePointerUp.bind(this);
    this._onPointerCancel = this._handlePointerCancel.bind(this);
    this._onKeyDown = this._handleKeyDown.bind(this);
    this._onKeyUp = this._handleKeyUp.bind(this);
    this._onClick = this._handleClick.bind(this);
  }

  attach() {
    if (this._attached) return;
    this._el.addEventListener("pointerdown", this._onPointerDown);
    this._el.addEventListener("pointerup", this._onPointerUp);
    this._el.addEventListener("pointercancel", this._onPointerCancel);
    this._el.addEventListener("click", this._onClick);
    if (this._keyboardEnabled) {
      document.addEventListener("keydown", this._onKeyDown);
      document.addEventListener("keyup", this._onKeyUp);
    }
    this._attached = true;
  }

  detach() {
    if (!this._attached) return;
    this._el.removeEventListener("pointerdown", this._onPointerDown);
    this._el.removeEventListener("pointerup", this._onPointerUp);
    this._el.removeEventListener("pointercancel", this._onPointerCancel);
    this._el.removeEventListener("click", this._onClick);
    if (this._keyboardEnabled) {
      document.removeEventListener("keydown", this._onKeyDown);
      document.removeEventListener("keyup", this._onKeyUp);
    }
    this._attached = false;
    this._pointerDown = false;
    this._spaceDown = false;
  }

  _handlePointerDown(evt) {
    if (this._pointerDown) return;
    this._pointerDown = true;
    this._toggleActive = false; // pointer takes over from toggle
    this._el.setPointerCapture?.(evt.pointerId);
    this._onAction("start");
  }

  _handlePointerUp() {
    if (!this._pointerDown) return;
    this._pointerDown = false;
    this._onAction("commit");
  }

  _handlePointerCancel() {
    if (!this._pointerDown) return;
    this._pointerDown = false;
    this._onAction("cancel");
  }

  _handleKeyDown(evt) {
    if (this._pointerDown) return; // pointer in progress
    if (evt.code !== "Space" || evt.repeat) return;
    // Don't capture Space inside form controls.
    const tag = document.activeElement?.tagName ?? "";
    if (["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(tag)) return;
    if (this._spaceDown) return;
    this._spaceDown = true;
    evt.preventDefault();
    this._onAction("start");
  }

  _handleKeyUp(evt) {
    if (evt.code !== "Space" || !this._spaceDown) return;
    this._spaceDown = false;
    this._onAction("commit");
  }

  /**
   * Accessible click-toggle for switch/keyboard users who cannot hold.
   */
  _handleClick() {
    if (this._pointerDown || this._spaceDown) return; // handled by other paths
    if (this._toggleActive) {
      this._toggleActive = false;
      this._onAction("commit");
    } else {
      this._toggleActive = true;
      this._onAction("start");
    }
  }
}
