const test = require("node:test");
const assert = require("node:assert/strict");

const pkg = require("../package.json");

test("package identity is Zeto", () => {
  assert.equal(pkg.name, "@zeaz/zeto");
  assert.match(pkg.description, /Zeto/i);
});

test("test runner is real", () => {
  assert.ok(pkg.scripts.test);
  assert.doesNotMatch(pkg.scripts.test, /No tests configured/);
});
