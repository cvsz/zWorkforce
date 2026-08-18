import assert from "node:assert/strict";
import test from "node:test";
import { TranscriptOverlay } from "../src/transcript_overlay.mjs";

test("TranscriptOverlay shows and stores captions", () => {
  const overlay = new TranscriptOverlay();
  const caption = overlay.showCaption("สวัสดีครับท่านผู้ใช้งาน", "th-TH");

  assert.ok(caption.id.startsWith("cap-"));
  assert.equal(caption.text, "สวัสดีครับท่านผู้ใช้งาน");
  assert.equal(caption.lang, "th-TH");
  assert.equal(caption.active, true);

  const recents = overlay.getRecentCaptions();
  assert.equal(recents.length, 1);
});

test("TranscriptOverlay dismisses caption", () => {
  const overlay = new TranscriptOverlay();
  overlay.showCaption("Hello World", "en-US");
  const dismissed = overlay.dismissCaption();

  assert.equal(dismissed.text, "Hello World");
  assert.equal(dismissed.active, false);
  assert.equal(overlay.currentCaption, null);
});
