import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createSkillCatalog,
  DuplicateSkillError,
  SkillNotFoundError,
  ToolNotAllowedError,
  ApprovalRequiredError
} from '../src/skill-catalog.mjs';

const READ_SKILL = {
  id: 'dev.zworkforce.zarvis.skill.research.web',
  version: '1.0.0',
  name: 'Web Research',
  domain: 'research',
  description: 'Bounded web search with provenance.',
  input_schema: { type: 'object' },
  output_schema: { type: 'object' },
  capability_allowlist: ['web.search', 'web.fetch'],
  mutability: 'read',
  timeout_seconds: 30,
  max_concurrency: 2,
  retry_policy: { max_attempts: 2, backoff: 'exponential', base_delay_seconds: 1 },
  idempotency_strategy: 'idempotency_key',
  audit_events: ['skill.research.started', 'skill.research.completed'],
  owner: 'zarvis-team',
  rollback_policy: 'none',
};

const WRITE_SKILL = {
  ...READ_SKILL,
  id: 'dev.zworkforce.zarvis.skill.memory.write',
  name: 'Memory Write',
  domain: 'memory',
  capability_allowlist: ['memory.write'],
  mutability: 'write',
  approval_rule: 'human_required',
  rollback_policy: 'compensating_transaction',
  audit_events: ['skill.memory.write.started', 'skill.memory.write.completed'],
};

test('register/get round-trip', () => {
  const catalog = createSkillCatalog();
  catalog.register(READ_SKILL);
  const skill = catalog.get(READ_SKILL.id, READ_SKILL.version);
  assert.deepEqual(skill, READ_SKILL);
});

test('DuplicateSkillError on collision', () => {
  const catalog = createSkillCatalog();
  catalog.register(READ_SKILL);
  assert.throws(() => {
    catalog.register(READ_SKILL);
  }, DuplicateSkillError);
});

test('SkillNotFoundError for missing', () => {
  const catalog = createSkillCatalog();
  assert.throws(() => {
    catalog.get('missing.id', '1.0.0');
  }, SkillNotFoundError);
});

test('assertToolAllowed passes when tool in allowlist', () => {
  const catalog = createSkillCatalog();
  assert.doesNotThrow(() => {
    catalog.assertToolAllowed(READ_SKILL, 'web.search');
  });
});

test('ToolNotAllowedError when tool not in allowlist', () => {
  const catalog = createSkillCatalog();
  assert.throws(() => {
    catalog.assertToolAllowed(READ_SKILL, 'web.write');
  }, ToolNotAllowedError);
});

test('assertApprovalValid passes for read skills with no token', () => {
  const catalog = createSkillCatalog();
  assert.doesNotThrow(() => {
    catalog.assertApprovalValid(READ_SKILL, undefined);
  });
});

test('assertApprovalValid passes for write skills with token', () => {
  const catalog = createSkillCatalog();
  assert.doesNotThrow(() => {
    catalog.assertApprovalValid(WRITE_SKILL, 'token123');
  });
});

test('ApprovalRequiredError for write skills missing token', () => {
  const catalog = createSkillCatalog();
  assert.throws(() => {
    catalog.assertApprovalValid(WRITE_SKILL, undefined);
  }, ApprovalRequiredError);
});

test('ApprovalRequiredError for write skills with empty string token', () => {
  const catalog = createSkillCatalog();
  assert.throws(() => {
    catalog.assertApprovalValid(WRITE_SKILL, '');
  }, ApprovalRequiredError);
});

test('list() returns sorted entries', () => {
  const catalog = createSkillCatalog();
  catalog.register(WRITE_SKILL);
  catalog.register(READ_SKILL);
  const list = catalog.list();
  assert.equal(list.length, 2);
  assert.equal(list[0].id, WRITE_SKILL.id);
  assert.equal(list[1].id, READ_SKILL.id);
});

test('findByDomain filters correctly', () => {
  const catalog = createSkillCatalog();
  catalog.register(WRITE_SKILL);
  catalog.register(READ_SKILL);
  const memorySkills = catalog.findByDomain('memory');
  assert.equal(memorySkills.length, 1);
  assert.equal(memorySkills[0].id, WRITE_SKILL.id);
});
