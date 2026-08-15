const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.join(__dirname, "..");

test("runtime and user-facing files use the Zeto product identity", () => {
  const files = [
    "public/index.html",
    "public/js/app.js",
    "src/aiAutoPoster.js",
    "src/contentGenerator.js",
    "src/db.js",
    "src/server.js",
    "Makefile",
  ];

  for (const file of files) {
    const content = fs.readFileSync(path.join(root, file), "utf8");
    assert.doesNotMatch(content, /zfbauto|ZeaZ FB Auto|FB Auto/i, file);
  }
});
