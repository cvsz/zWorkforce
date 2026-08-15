const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

test("local object storage round-trips media and blocks traversal", async () => {
  const { LocalObjectStorage } = require("../src/storage/localObjectStorage");
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "zeto-storage-"));
  try {
    const storage = new LocalObjectStorage(root);
    await storage.put(
      "brands/zato/assets/example.txt",
      Buffer.from("content"),
      {
        contentType: "text/plain",
      },
    );
    const value = await storage.get("brands/zato/assets/example.txt");
    assert.equal(value.body.toString(), "content");
    assert.equal(value.contentType, "text/plain");
    await assert.rejects(
      () => storage.put("../escape", Buffer.from("bad")),
      /invalid storage key/i,
    );
  } finally {
    await fs.rm(root, { recursive: true, force: true });
  }
});
