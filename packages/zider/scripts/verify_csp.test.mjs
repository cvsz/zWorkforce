import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const manifestPath = path.resolve(__dirname, "../extension/manifest.json");

test("Manifest V3 enforces strict CSP without unsafe directives", () => {
  const raw = fs.readFileSync(manifestPath, "utf-8");
  const manifest = JSON.parse(raw);

  assert.equal(manifest.manifest_version, 3);
  assert.ok(manifest.content_security_policy);
  const csp = manifest.content_security_policy.extension_pages;

  assert.ok(csp.includes("script-src 'self'"));
  assert.ok(!csp.includes("'unsafe-eval'"));
  assert.ok(csp.includes("object-src 'self'"));
});
