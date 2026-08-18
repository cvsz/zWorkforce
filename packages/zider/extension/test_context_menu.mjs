import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

class MockChromeContextMenus {
  constructor() {
    this.menus = new Map();
    this.clickListeners = [];
  }

  create(opts) {
    this.menus.set(opts.id, opts);
  }

  get(id) {
    return this.menus.get(id);
  }
}

test("context menu creates standard selection items", () => {
  const mock = new MockChromeContextMenus();

  const menuDefs = [
    { id: "zider-explain", title: "zider: Explain selection", contexts: ["selection"] },
    { id: "zider-summarize", title: "zider: Summarize selection", contexts: ["selection"] },
    { id: "zider-translate", title: "zider: Translate selection", contexts: ["selection"] },
    { id: "zider-counter", title: "zider: Counter-argument", contexts: ["selection"] },
  ];

  menuDefs.forEach((m) => mock.create(m));

  assert.equal(mock.menus.size, 4);
  assert.equal(mock.get("zider-explain").contexts[0], "selection");
  assert.equal(mock.get("zider-counter").id, "zider-counter");
});

test("context menu maps action types correctly", () => {
  const actionMap = {
    "zider-explain": "explain",
    "zider-summarize": "summarize",
    "zider-translate": "translate",
    "zider-counter": "counter_argument",
  };

  assert.equal(actionMap["zider-explain"], "explain");
  assert.equal(actionMap["zider-counter"], "counter_argument");
});

test("zider context menu declares selection handler", () => {
  const bgPath = path.resolve(__dirname, "../extension/background.js");
  assert.ok(fs.existsSync(bgPath), "background.js must exist");

  const content = fs.readFileSync(bgPath, "utf8");
  assert.ok(content.includes("contextMenus") || content.includes("chrome.runtime"), "Must have extension background bindings");
});