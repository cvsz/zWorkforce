/**
 * Z.A.R.V.I.S. skill catalog — registry and policy enforcement for runtime skills.
 *
 * Skills are deny-by-default. A skill may only be invoked if:
 * 1. Its id+version appear in this catalog.
 * 2. The tool call is in its capability_allowlist.
 * 3. Write skills have a valid, unexpired approval_token.
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

export class SkillCatalog {
  constructor() {
    this.skills = new Map();
  }

  _getKey(id, version) {
    return `${id}@${version}`;
  }

  register(manifest) {
    if (!manifest || !manifest.id || !manifest.version) {
      throw new Error("Invalid manifest");
    }
    const key = this._getKey(manifest.id, manifest.version);
    if (this.skills.has(key)) {
      throw new DuplicateSkillError(`Skill ${key} already registered`);
    }
    this.skills.set(key, manifest);
  }

  get(id, version) {
    const key = this._getKey(id, version);
    const manifest = this.skills.get(key);
    if (!manifest) {
      throw new SkillNotFoundError(`Skill ${key} not found`);
    }
    return manifest;
  }

  list() {
    return Array.from(this.skills.values())
      .map(manifest => ({
        id: manifest.id,
        version: manifest.version,
        domain: manifest.domain,
        mutability: manifest.mutability,
        name: manifest.name
      }))
      .sort((a, b) => {
        if (a.id < b.id) return -1;
        if (a.id > b.id) return 1;
        return a.version.localeCompare(b.version);
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
        throw new ApprovalRequiredError("Valid approval token required for write skill");
      }
    }
  }
}

export function createSkillCatalog() {
  return new SkillCatalog();
}
