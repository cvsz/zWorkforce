import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const schemaDir = new URL("../schemas/", import.meta.url);

async function readSchema(name) {
  return JSON.parse(await readFile(new URL(name, schemaDir), "utf8"));
}

test("skill manifest schema validation", async () => {
  const schema = await readSchema("zarvis.skill.manifest.v1.schema.json");
  
  assert.ok(schema.$schema, "missing $schema");
  assert.ok(schema.required.includes("id"));
  assert.ok(schema.required.includes("version"));
  assert.ok(schema.required.includes("mutability"));
  assert.ok(schema.required.includes("capability_allowlist"));
  assert.ok(!schema.required.includes("approval_rule"), "approval_rule should not be required");
});

test("skill invocation schema validation", async () => {
  const schema = await readSchema("zarvis.skill.invocation.v1.schema.json");
  
  assert.ok(schema.$schema, "missing $schema");
  assert.ok(schema.properties.approval_token, "missing approval_token in properties");
});

test("skill result schema validation", async () => {
  const schema = await readSchema("zarvis.skill.result.v1.schema.json");
  
  assert.ok(schema.$schema, "missing $schema");
  assert.ok(schema.properties.status.enum.includes("denied"), "status enum missing 'denied'");
});
