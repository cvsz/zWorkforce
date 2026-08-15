const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const path = require("node:path");
const test = require("node:test");

const cryptoModule = path.join(__dirname, "..", "src", "crypto.js");

test("production refuses to initialize encryption without an explicit key", () => {
  const env = { ...process.env, NODE_ENV: "production" };
  delete env.SECRET_ENCRYPTION_KEY;
  delete env.FACEBOOK_APP_SECRET;

  const result = spawnSync(
    process.execPath,
    ["-e", `require(${JSON.stringify(cryptoModule)})`],
    {
      env,
      encoding: "utf8",
    },
  );

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /SECRET_ENCRYPTION_KEY/);
});

test("production refuses a weak encryption key", () => {
  const result = spawnSync(
    process.execPath,
    ["-e", `require(${JSON.stringify(cryptoModule)})`],
    {
      env: {
        ...process.env,
        NODE_ENV: "production",
        SECRET_ENCRYPTION_KEY: "too-short",
      },
      encoding: "utf8",
    },
  );
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /at least 32/);
});

test("encrypted values round-trip with authenticated encryption", () => {
  const script = [
    `const encryption = require(${JSON.stringify(cryptoModule)});`,
    "const value = 'provider-secret';",
    "const encrypted = encryption.encrypt(value);",
    "if (encrypted === value || encryption.decrypt(encrypted) !== value) process.exit(1);",
  ].join(" ");
  const result = spawnSync(process.execPath, ["-e", script], {
    env: {
      ...process.env,
      SECRET_ENCRYPTION_KEY: "test-only-key-with-at-least-32-characters",
    },
    encoding: "utf8",
  });

  assert.equal(result.status, 0, result.stderr);
});
