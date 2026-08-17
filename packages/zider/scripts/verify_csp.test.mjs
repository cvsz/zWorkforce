import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

test('zider extension manifest.json meets strict Manifest V3 invariants', () => {
  const manifestPath = path.resolve('extension/manifest.json');
  assert.ok(fs.existsSync(manifestPath), 'manifest.json must exist');
  
  const content = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  assert.equal(content.manifest_version, 3, 'Must be Manifest V3');
  assert.ok(content.background && content.background.service_worker, 'Must declare service_worker');
  assert.ok(content.name.includes('zider'), 'Must contain zider name');
});
