import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { createToolRegistry, DuplicateToolError, ToolNotFoundError, ApprovalRequiredError, ToolNotGrantedError } = require('../src/domain/toolRegistry.js');

const fakeTool = {
  name: 'test.read',
  description: 'Test read tool',
  mutating: false,
  schema: null,
  handler: async (args) => ({ result: args.input ?? 'ok' }),
};

const fakeMutatingTool = {
  name: 'test.write',
  description: 'Test write tool',
  mutating: true,
  schema: null,
  handler: async (args) => ({ written: true }),
};

describe('ToolRegistry', () => {
  it('register/invoke round-trip for read tool', async () => {
    const registry = createToolRegistry();
    registry.register(fakeTool);
    const result = await registry.invoke('test.read', { input: 'hello' }, {});
    assert.deepEqual(result, { result: 'hello' });
  });

  it('DuplicateToolError on double-register', () => {
    const registry = createToolRegistry();
    registry.register(fakeTool);
    assert.throws(() => registry.register(fakeTool), DuplicateToolError);
  });

  it('ToolNotFoundError for unknown tool', async () => {
    const registry = createToolRegistry();
    await assert.rejects(async () => registry.invoke('unknown', {}, {}), ToolNotFoundError);
  });

  it('ApprovalRequiredError when mutating tool invoked without approvalRecord', async () => {
    const registry = createToolRegistry();
    registry.register(fakeMutatingTool);
    await assert.rejects(async () => registry.invoke('test.write', {}, {}), ApprovalRequiredError);
  });

  it('ApprovalRequiredError when approvalRecord is null/empty', async () => {
    const registry = createToolRegistry();
    registry.register(fakeMutatingTool);
    await assert.rejects(async () => registry.invoke('test.write', {}, {}, { approvalRecord: null }), ApprovalRequiredError);
  });

  it('Mutating tool succeeds with valid approvalRecord', async () => {
    const registry = createToolRegistry();
    registry.register(fakeMutatingTool);
    const res = await registry.invoke('test.write', {}, {}, { approvalRecord: { approved: true } });
    assert.deepEqual(res, { written: true });
  });

  it('assertGranted passes when tool in sessionCapabilities', () => {
    const registry = createToolRegistry();
    registry.assertGranted('test.read', ['test.read']);
  });

  it('ToolNotGrantedError when not in sessionCapabilities', () => {
    const registry = createToolRegistry();
    assert.throws(() => registry.assertGranted('test.read', []), ToolNotGrantedError);
  });

  it('list() returns sorted names', () => {
    const registry = createToolRegistry();
    registry.register({ ...fakeTool, name: 'b' });
    registry.register({ ...fakeTool, name: 'a' });
    const list = registry.list();
    assert.equal(list.length, 2);
    assert.equal(list[0].name, 'a');
    assert.equal(list[1].name, 'b');
  });

  it('invoke with handler error propagates correctly', async () => {
    const registry = createToolRegistry();
    registry.register({
      ...fakeTool,
      handler: async () => { throw new Error('handler failed'); }
    });
    await assert.rejects(async () => registry.invoke('test.read', {}, {}), /handler failed/);
  });

  it('Credential keys in args do not appear in any thrown error messages', async () => {
    const registry = createToolRegistry();
    registry.register({
      ...fakeTool,
      handler: async (args) => {
        throw new Error(`Failed to use token: ${args.token} and secret: ${args.secret}`);
      }
    });
    try {
      await registry.invoke('test.read', { token: 'my-super-secret-token', secret: '123' }, {});
      assert.fail('Should have thrown');
    } catch (err) {
      assert.ok(!err.message.includes('my-super-secret-token'), 'Token should be redacted');
      assert.ok(!err.message.includes('123'), 'Secret should be redacted');
    }
  });
});
