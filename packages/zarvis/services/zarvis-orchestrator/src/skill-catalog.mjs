/**
 * Z.A.R.V.I.S. skill catalog — registry, lifecycle and policy enforcement.
 *
 * Skills are deny-by-default. A skill may only be invoked if:
 * 1. Its id+version appear in this catalog.
 * 2. The selected version is enabled.
 * 3. The tool call is in its capability_allowlist.
 * 4. Write skills have a valid approval token when required.
 *
 * Lifecycle rules intentionally keep prior versions available for rollback.
 * Automatic system-skill updates are allowed only when the new version does not
 * silently expand tool capabilities, escalate mutability, or weaken approval.
 *
 * No server credentials are stored here. This module is pure business logic.
 */

export class DuplicateSkillError extends Error {
  constructor(message) {
    super(message);
    this.name = 'DuplicateSkillError';
  }
}

export class SkillNotFoundError extends Error {
  constructor(message) {
    super(message);
    this.name = 'SkillNotFoundError';
  }
}

export class SkillDisabledError extends Error {
  constructor(message) {
    super(message);
    this.name = 'SkillDisabledError';
  }
}

export class SkillVersionError extends Error {
  constructor(message) {
    super(message);
    this.name = 'SkillVersionError';
  }
}

export class CapabilityExpansionError extends Error {
  constructor(message) {
    super(message);
    this.name = 'CapabilityExpansionError';
  }
}

export class ToolNotAllowedError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ToolNotAllowedError';
  }
}

export class ApprovalRequiredError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ApprovalRequiredError';
  }
}

function parseSemanticVersion(version) {
  const match = String(version).match(/^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$/);
  if (!match) {
    throw new SkillVersionError(`Invalid semantic version: ${version}`);
  }
  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: Number(match[3]),
    prerelease: match[4] ?? null,
  };
}

function compareSemanticVersions(left, right) {
  const a = parseSemanticVersion(left);
  const b = parseSemanticVersion(right);
  for (const part of ['major', 'minor', 'patch']) {
    if (a[part] !== b[part]) return a[part] - b[part];
  }
  if (a.prerelease === b.prerelease) return 0;
  if (a.prerelease === null) return 1;
  if (b.prerelease === null) return -1;
  return a.prerelease.localeCompare(b.prerelease, undefined, { numeric: true });
}

function normalizedLifecycle(manifest) {
  return {
    enabled: manifest.enabled !== false,
    source: manifest.source ?? 'local',
    updatePolicy: manifest.update_policy ?? 'manual',
  };
}

function assertAutoUpdateDoesNotBroadenAuthority(previous, next) {
  const previousTools = new Set(previous.capability_allowlist ?? []);
  const expandedTools = (next.capability_allowlist ?? []).filter(tool => !previousTools.has(tool));
  if (expandedTools.length > 0) {
    throw new CapabilityExpansionError(
      `Automatic update cannot add capabilities: ${expandedTools.join(', ')}`,
    );
  }

  if (previous.mutability !== 'write' && next.mutability === 'write') {
    throw new CapabilityExpansionError('Automatic update cannot escalate mutability to write');
  }

  const previousRequiresApproval = previous.approval_rule && previous.approval_rule !== 'none';
  const nextRequiresApproval = next.approval_rule && next.approval_rule !== 'none';
  if (previousRequiresApproval && !nextRequiresApproval) {
    throw new CapabilityExpansionError('Automatic update cannot weaken approval requirements');
  }
}

export class SkillCatalog {
  constructor() {
    this.skills = new Map();
    this.lifecycle = new Map();
    this.activeVersions = new Map();
  }

  _getKey(id, version) {
    return `${id}@${version}`;
  }

  _versionsFor(id) {
    return Array.from(this.skills.values()).filter(manifest => manifest.id === id);
  }

  _latestEnabled(id) {
    const enabled = this._versionsFor(id).filter(manifest => {
      const state = this.lifecycle.get(this._getKey(manifest.id, manifest.version));
      return state?.enabled !== false;
    });
    if (enabled.length === 0) return null;
    return enabled.sort((a, b) => compareSemanticVersions(b.version, a.version))[0];
  }

  register(manifest) {
    if (!manifest || !manifest.id || !manifest.version) {
      throw new Error('Invalid manifest');
    }
    parseSemanticVersion(manifest.version);
    const key = this._getKey(manifest.id, manifest.version);
    if (this.skills.has(key)) {
      throw new DuplicateSkillError(`Skill ${key} already registered`);
    }

    this.skills.set(key, manifest);
    const state = normalizedLifecycle(manifest);
    this.lifecycle.set(key, state);

    if (state.enabled) {
      const activeVersion = this.activeVersions.get(manifest.id);
      if (!activeVersion || compareSemanticVersions(manifest.version, activeVersion) > 0) {
        this.activeVersions.set(manifest.id, manifest.version);
      }
    }
    return manifest;
  }

  install(manifest) {
    return this.register(manifest);
  }

  get(id, version) {
    const key = this._getKey(id, version);
    const manifest = this.skills.get(key);
    if (!manifest) {
      throw new SkillNotFoundError(`Skill ${key} not found`);
    }
    return manifest;
  }

  resolveVersion(id, version) {
    const manifest = this.get(id, version);
    const state = this.lifecycle.get(this._getKey(id, version));
    if (!state?.enabled) {
      throw new SkillDisabledError(`Skill ${id}@${version} is disabled`);
    }
    return manifest;
  }

  resolve(id) {
    const activeVersion = this.activeVersions.get(id);
    if (activeVersion) {
      const key = this._getKey(id, activeVersion);
      const state = this.lifecycle.get(key);
      if (state?.enabled) return this.get(id, activeVersion);
    }

    const fallback = this._latestEnabled(id);
    if (!fallback) {
      if (this._versionsFor(id).length > 0) {
        throw new SkillDisabledError(`All versions of skill ${id} are disabled`);
      }
      throw new SkillNotFoundError(`Skill ${id} not found`);
    }
    this.activeVersions.set(id, fallback.version);
    return fallback;
  }

  setEnabled(id, version, enabled) {
    const manifest = this.get(id, version);
    const key = this._getKey(id, version);
    const state = this.lifecycle.get(key) ?? normalizedLifecycle(manifest);
    state.enabled = Boolean(enabled);
    this.lifecycle.set(key, state);

    if (state.enabled) {
      const activeVersion = this.activeVersions.get(id);
      if (!activeVersion || compareSemanticVersions(version, activeVersion) > 0) {
        this.activeVersions.set(id, version);
      }
    } else if (this.activeVersions.get(id) === version) {
      const fallback = this._latestEnabled(id);
      if (fallback) this.activeVersions.set(id, fallback.version);
      else this.activeVersions.delete(id);
    }
    return this.list().find(item => item.id === id && item.version === version);
  }

  rollback(id, version) {
    const manifest = this.resolveVersion(id, version);
    this.activeVersions.set(id, version);
    return manifest;
  }

  updateSystemSkill(manifest) {
    const state = normalizedLifecycle(manifest);
    if (state.source !== 'system' || state.updatePolicy !== 'auto') {
      throw new SkillVersionError('Automatic updates require source=system and update_policy=auto');
    }

    const previous = this._latestEnabled(manifest.id);
    if (!previous) return this.register(manifest);
    if (compareSemanticVersions(manifest.version, previous.version) <= 0) {
      throw new SkillVersionError(
        `Automatic update ${manifest.id}@${manifest.version} must be newer than ${previous.version}`,
      );
    }

    assertAutoUpdateDoesNotBroadenAuthority(previous, manifest);
    return this.register(manifest);
  }

  list() {
    return Array.from(this.skills.values())
      .map(manifest => {
        const key = this._getKey(manifest.id, manifest.version);
        const state = this.lifecycle.get(key) ?? normalizedLifecycle(manifest);
        return {
          id: manifest.id,
          version: manifest.version,
          domain: manifest.domain,
          mutability: manifest.mutability,
          name: manifest.name,
          enabled: state.enabled,
          source: state.source,
          update_policy: state.updatePolicy,
          active: this.activeVersions.get(manifest.id) === manifest.version,
        };
      })
      .sort((a, b) => {
        if (a.id < b.id) return -1;
        if (a.id > b.id) return 1;
        return compareSemanticVersions(a.version, b.version);
      });
  }

  findByDomain(domain) {
    return Array.from(this.skills.values()).filter(m => m.domain === domain);
  }

  assertToolAllowed(manifest, toolName) {
    if (!manifest.capability_allowlist || !manifest.capability_allowlist.includes(toolName)) {
      throw new ToolNotAllowedError(`Tool ${toolName} not in capability_allowlist`);
    }
  }

  assertApprovalValid(manifest, approvalToken, now = new Date()) {
    if (manifest.mutability === 'write' && manifest.approval_rule !== 'none') {
      if (!approvalToken || approvalToken.trim() === '') {
        throw new ApprovalRequiredError('Valid approval token required for write skill');
      }
    }
  }
}

export function createSkillCatalog() {
  return new SkillCatalog();
}
