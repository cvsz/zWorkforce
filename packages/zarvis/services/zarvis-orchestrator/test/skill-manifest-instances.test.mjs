import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createSkillCatalog } from '../src/skill-catalog.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SKILLS_DIR = join(__dirname, '../../../skills');
const DOMAINS = ['conversation', 'memory', 'research', 'code', 'operations', 'productivity'];

describe('Runtime Skill Manifest Instances', () => {
  it('loads and registers every domain manifest cleanly into the catalog', async () => {
    const catalog = createSkillCatalog();
    
    for (const domain of DOMAINS) {
      const manifestPath = join(SKILLS_DIR, domain, 'skill.json');
      const raw = await readFile(manifestPath, 'utf8');
      const manifest = JSON.parse(raw);
      
      assert.equal(manifest.domain, domain, `manifest domain mismatch for ${domain}`);
      assert.ok(manifest.id.startsWith('dev.zworkforce.zarvis.skill.'), `invalid id prefix for ${manifest.id}`);
      assert.ok(manifest.capability_allowlist.length > 0, `empty allowlist for ${manifest.id}`);
      
      catalog.register(manifest);
      const retrieved = catalog.get(manifest.id, manifest.version);
      assert.equal(retrieved.name, manifest.name);
    }
    
    const list = catalog.list();
    assert.equal(list.length, DOMAINS.length);
  });
});
