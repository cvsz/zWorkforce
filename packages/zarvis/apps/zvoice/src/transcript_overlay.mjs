/**
 * transcript_overlay.mjs
 *
 * Multi-Language Live Transcription Overlay for Z.A.R.V.I.S. Voice UI.
 * Handles BCP-47 language tag switching, timed caption display, and smooth fade-out.
 */

export class TranscriptOverlay {
  constructor(options = {}) {
    this.container = options.container || null;
    this.defaultDurationMs = Number(options.defaultDurationMs || 4000);
    this.currentCaption = null;
    this.history = [];
  }

  showCaption(text, lang = "th-TH", durationMs = null) {
    if (!text || typeof text !== "string") return null;

    const caption = {
      id: `cap-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      text: text.trim(),
      lang: String(lang || "th-TH"),
      shownAt: new Date().toISOString(),
      durationMs: durationMs || this.defaultDurationMs,
      active: true,
    };

    this.currentCaption = caption;
    this.history.push(caption);

    // Limit history memory buffer
    if (this.history.length > 50) {
      this.history.shift();
    }

    return caption;
  }

  dismissCaption() {
    if (this.currentCaption) {
      this.currentCaption.active = false;
      const dismissed = this.currentCaption;
      this.currentCaption = null;
      return dismissed;
    }
    return null;
  }

  getRecentCaptions(limit = 5) {
    return this.history.slice(-limit);
  }
}
