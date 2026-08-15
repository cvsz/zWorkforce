const fs = require("node:fs/promises");
const path = require("node:path");
const { ObjectStorage } = require("./objectStorage");

class LocalObjectStorage extends ObjectStorage {
  constructor(root) {
    super();
    this.root = path.resolve(root);
  }

  resolve(key) {
    if (!key || path.isAbsolute(key) || key.includes("\\"))
      throw new Error("Invalid storage key");
    const normalized = path.posix.normalize(key);
    if (normalized.startsWith("../") || normalized === "..")
      throw new Error("Invalid storage key");
    const resolved = path.resolve(this.root, normalized);
    if (!resolved.startsWith(`${this.root}${path.sep}`))
      throw new Error("Invalid storage key");
    return resolved;
  }

  async put(key, body, { contentType = "application/octet-stream" } = {}) {
    const file = this.resolve(key);
    await fs.mkdir(path.dirname(file), { recursive: true });
    await fs.writeFile(file, body, { flag: "wx" });
    await fs.writeFile(
      `${file}.metadata.json`,
      JSON.stringify({ contentType }),
      { flag: "wx" },
    );
    return { key, contentType, size: Buffer.byteLength(body) };
  }

  async get(key) {
    const file = this.resolve(key);
    const [body, metadata] = await Promise.all([
      fs.readFile(file),
      fs.readFile(`${file}.metadata.json`, "utf8").then(JSON.parse),
    ]);
    return { key, body, contentType: metadata.contentType };
  }

  async delete(key) {
    const file = this.resolve(key);
    await Promise.all([fs.unlink(file), fs.unlink(`${file}.metadata.json`)]);
  }
}

module.exports = { LocalObjectStorage };
