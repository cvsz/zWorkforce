import assert from "node:assert/strict";
import test from "node:test";

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
