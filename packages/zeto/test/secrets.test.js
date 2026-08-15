const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { readSecret } = require("../src/security/secrets");

test("secret resolver supports mounted files without exposing content", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "zeto-secret-"));
  const file = path.join(directory, "token");
  await fs.writeFile(file, "mounted-secret\n", { mode: 0o600 });
  const env = {
    PROVIDER_TOKEN: "environment-secret",
    PROVIDER_TOKEN_FILE: file,
  };
  assert.equal(readSecret("PROVIDER_TOKEN", { env }), "mounted-secret");
  await fs.rm(directory, { recursive: true });
});

test("secret resolver rejects empty and oversized mounted secrets", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "zeto-secret-"));
  const empty = path.join(directory, "empty");
  await fs.writeFile(empty, "\n");
  assert.throws(
    () => readSecret("TOKEN", { env: { TOKEN_FILE: empty } }),
    /empty/,
  );
  await fs.rm(directory, { recursive: true });
});
