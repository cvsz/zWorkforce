/**
 * Tests for graceful shutdown coordinator.
 * @see exec-planing.md Phase 9 — Enterprise Production Hardening
 */
import { describe, it, mock } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { registerShutdown } = require('../src/shutdown.js');

function makeServer(closeDelay = 0) {
  return {
    close(cb) { setTimeout(cb, closeDelay); }
  };
}

function makePool(shouldFail = false) {
  return {
    async end() {
      if (shouldFail) throw new Error('pool close failed');
    }
  };
}

function makeProc() {
  const events = {};
  let exitCode = null;
  return {
    once(event, handler) { events[event] = handler; },
    emit(event) { return events[event]?.(event); },
    exit(code) { exitCode = code; },
    get exitCode() { return exitCode; },
  };
}

describe('registerShutdown', () => {
  it('exits 0 on clean SIGTERM', async () => {
    const proc = makeProc();
    const logs = [];
    registerShutdown({
      server: makeServer(0),
      pool: makePool(),
      log: (m) => logs.push(m),
      timeoutMs: 5000,
      proc,
    });
    await proc.emit('SIGTERM');
    await new Promise((r) => setTimeout(r, 50));
    assert.equal(proc.exitCode, 0);
  });

  it('exits 0 on SIGINT', async () => {
    const proc = makeProc();
    registerShutdown({
      server: makeServer(0),
      log: () => {},
      timeoutMs: 5000,
      proc,
    });
    await proc.emit('SIGINT');
    await new Promise((r) => setTimeout(r, 50));
    assert.equal(proc.exitCode, 0);
  });

  it('exits 0 when pool.end() throws', async () => {
    const proc = makeProc();
    const logs = [];
    registerShutdown({
      server: makeServer(0),
      pool: makePool(true),
      log: (m) => logs.push(m),
      timeoutMs: 5000,
      proc,
    });
    await proc.emit('SIGTERM');
    await new Promise((r) => setTimeout(r, 50));
    assert.equal(proc.exitCode, 0);
    assert.ok(logs.some((l) => l.includes('pool close failed')));
  });

  it('second signal is ignored', async () => {
    const proc = makeProc();
    let exitCount = 0;
    const origExit = proc.exit.bind(proc);
    proc.exit = (code) => { exitCount++; origExit(code); };
    registerShutdown({ server: makeServer(0), log: () => {}, timeoutMs: 5000, proc });
    proc.emit('SIGTERM');
    proc.emit('SIGTERM'); // should be ignored
    await new Promise((r) => setTimeout(r, 100));
    assert.equal(exitCount, 1);
  });

  it('logs shutdown sequence without credential leak', async () => {
    const proc = makeProc();
    const logs = [];
    registerShutdown({ server: makeServer(0), log: (m) => logs.push(m), timeoutMs: 5000, proc });
    await proc.emit('SIGTERM');
    await new Promise((r) => setTimeout(r, 50));
    const combined = logs.join(' ');
    assert.ok(!combined.includes('token'));
    assert.ok(!combined.includes('secret'));
    assert.ok(!combined.includes('password'));
  });
});
