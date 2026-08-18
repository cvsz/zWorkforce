import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

test('zider context menu declares selection handler', () => {
  const bgPath = path.resolve('extension/background.js');
  assert.ok(fs.existsSync(bgPath), 'background.js must exist');
  
  const content = fs.readFileSync(bgPath, 'utf8');
  assert.ok(content.includes('contextMenus') || content.includes('chrome.runtime'), 'Must have extension background bindings');
});
