import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { ZarvisOrchestrator } from '../src/orchestrator.mjs';
import { ApprovalRequiredError, SkillDisabledError } from '../src/skill-catalog.mjs';

const SAMPLE_SKILL = {
  id: 'dev.zworkforce.zarvis.skill.conversation.summarize',
  version: '1.0.0',
  name: 'Conversation Summarizer',
  domain: 'conversation',
  description: 'Test skill',
  input_schema: { type: 'object' },
  output_schema: { type: 'object' },
  capability_allowlist: ['conversation.summarize'],
  mutability: 'read',
  timeout_seconds: 15,
  max_concurrency: 10,
  retry_policy: { max_attempts: 2, backoff: 'exponential', base_delay_seconds: 0.5 },
  idempotency_strategy: 'idempotency_key',
  audit_events: ['zarvis.conversation.summarized.v1'],
  owner: 'zarvis-core',
  rollback_policy: 'none',
};

const MUTATING_SKILL = {
  ...SAMPLE_SKILL,
  id: 'dev.zworkforce.zarvis.skill.memory.write',
  name: 'Memory Write',
  domain: 'memory',
  mutability: 'write',
  approval_rule: 'human_required',
};

describe('ZarvisOrchestrator.executeSkill', () => {
  it('executes a read skill and returns a valid skill result envelope', async () => {
    const orchestrator = new ZarvisOrchestrator();
    orchestrator.registerSkill(SAMPLE_SKILL);

    const result = await orchestrator.executeSkill({
      skillId: SAMPLE_SKILL.id,
      version: SAMPLE_SKILL.version,
      input: { turns: [] },
      actor: { tenant_id: 'tenant-test', type: 'user', id: 'user-1' },
      handler: async () => ({ summary: 'hello', key_points: ['point1'] }),
    });

    assert.equal(result.status, 'succeeded');
    assert.equal(result.skill_id, SAMPLE_SKILL.id);
    assert.equal(result.output.summary, 'hello');
  });

  it('uses the active enabled skill version when version is omitted', async () => {
    const orchestrator = new ZarvisOrchestrator();
    orchestrator.installSkill(SAMPLE_SKILL);
    orchestrator.installSkill({ ...SAMPLE_SKILL, version: '1.1.0' });

    const result = await orchestrator.executeSkill({
      skillId: SAMPLE_SKILL.id,
      input: { turns: [] },
      actor: { tenant_id: 'tenant-test', type: 'user', id: 'user-1' },
      handler: async () => ({ summary: 'active-version' }),
    });

    assert.equal(result.status, 'succeeded');
    assert.equal(result.skill_version, '1.1.0');
  });

  it('fails closed when an explicitly requested skill version is disabled', async () => {
    const orchestrator = new ZarvisOrchestrator();
    orchestrator.installSkill(SAMPLE_SKILL);
    orchestrator.setSkillEnabled(SAMPLE_SKILL.id, SAMPLE_SKILL.version, false);

    await assert.rejects(
      () => orchestrator.executeSkill({
        skillId: SAMPLE_SKILL.id,
        version: SAMPLE_SKILL.version,
        input: { turns: [] },
        actor: { tenant_id: 'tenant-test', type: 'user', id: 'user-1' },
        handler: async () => ({ summary: 'must-not-run' }),
      }),
      SkillDisabledError,
    );
  });

  it('rejects a mutating skill if approval token is missing', async () => {
    const orchestrator = new ZarvisOrchestrator();
    orchestrator.registerSkill(MUTATING_SKILL);

    await assert.rejects(
      () => orchestrator.executeSkill({
        skillId: MUTATING_SKILL.id,
        version: MUTATING_SKILL.version,
        input: { content: 'test' },
        actor: { tenant_id: 'tenant-test', type: 'user', id: 'user-1' },
        approvalToken: null,
        handler: async () => ({ proposal_id: '123' }),
      }),
      ApprovalRequiredError
    );
  });

  it('executes a mutating skill when a valid approval token is provided', async () => {
    const orchestrator = new ZarvisOrchestrator();
    orchestrator.registerSkill(MUTATING_SKILL);

    const result = await orchestrator.executeSkill({
      skillId: MUTATING_SKILL.id,
      version: MUTATING_SKILL.version,
      input: { content: 'test' },
      actor: { tenant_id: 'tenant-test', type: 'user', id: 'user-1' },
      approvalToken: 'appr_valid_token_123',
      handler: async () => ({ proposal_id: 'p_123', status: 'proposed' }),
    });

    assert.equal(result.status, 'succeeded');
    assert.equal(result.output.proposal_id, 'p_123');
  });
});
