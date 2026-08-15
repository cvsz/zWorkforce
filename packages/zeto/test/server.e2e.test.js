const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const net = require("node:net");
const path = require("node:path");
const test = require("node:test");

const databaseUrl = process.env.TEST_DATABASE_URL;
const integrationTest = databaseUrl ? test : test.skip;

async function availablePort() {
  const server = net.createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  await new Promise((resolve) => server.close(resolve));
  return port;
}

async function waitFor(url, child, getStartupError) {
  for (let attempt = 0; attempt < 300; attempt += 1) {
    if (child.exitCode !== null) {
      throw new Error(
        `Server exited with code ${child.exitCode} before readiness: ${getStartupError()}`,
      );
    }
    try {
      const response = await fetch(url);
      if (response.ok) return response;
    } catch {
      // Server startup is still in progress.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

integrationTest(
  "production server migrates, serves v1, and shuts down gracefully",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const setupPool = createPool({ connectionString: databaseUrl, max: 1 });
    await migrate(setupPool);
    await setupPool.query("TRUNCATE user_sessions, users, roles CASCADE");
    await setupPool.end();
    const port = await availablePort();
    const child = spawn(
      process.execPath,
      [path.join(__dirname, "..", "src", "server.js")],
      {
        env: {
          ...process.env,
          NODE_ENV: "production",
          PORT: String(port),
          DATABASE_URL: databaseUrl,
          SECRET_ENCRYPTION_KEY:
            "test-server-encryption-key-with-32-characters",
          ADMIN_INITIAL_PASSWORD: "test-admin-password",
          METRICS_TOKEN: "test-metrics-token",
          LOG_LEVEL: "silent",
        },
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    try {
      const ready = await waitFor(
        `http://127.0.0.1:${port}/ready`,
        child,
        () => stderr,
      );
      const readyBody = await ready.json();
      assert.equal(readyBody.ready, true);

      const login = await fetch(`http://127.0.0.1:${port}/api/auth/login`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          username: "admin",
          password: "test-admin-password",
        }),
      });
      assert.equal(login.status, 200);
      const token = (await login.json()).data.token;
      const settingsUpdate = await fetch(
        `http://127.0.0.1:${port}/api/settings`,
        {
          method: "PATCH",
          headers: {
            authorization: `Bearer ${token}`,
            "content-type": "application/json",
          },
          body: JSON.stringify({
            schedulerEnabled: true,
            facebookAccessToken: "must-never-leave-server",
          }),
        },
      );
      const settingsUpdateBody = await settingsUpdate.json();
      assert.equal(settingsUpdate.status, 200);
      assert.equal(settingsUpdateBody.data.facebookAccessToken, undefined);
      const settingsRead = await fetch(
        `http://127.0.0.1:${port}/api/settings`,
        { headers: { authorization: `Bearer ${token}` } },
      );
      assert.equal(
        (await settingsRead.json()).data.facebookAccessToken,
        undefined,
      );
      const created = await fetch(`http://127.0.0.1:${port}/v1/brands`, {
        method: "POST",
        headers: {
          authorization: `Bearer ${token}`,
          "content-type": "application/json",
          "idempotency-key": `zato-e2e-${Date.now()}`,
        },
        body: JSON.stringify({
          name: "zato",
          niche: "Niche Content",
          colors: ["#ffffff", "#e9d5ff"],
        }),
      });
      assert.equal(created.status, 201);
      assert.equal((await created.json()).data.name, "zato");

      child.kill("SIGTERM");
      const [code, signal] = await new Promise((resolve) =>
        child.once("exit", (...args) => resolve(args)),
      );
      assert.equal(signal, null);
      assert.equal(code, 0, stderr);
    } finally {
      if (child.exitCode === null) child.kill("SIGKILL");
    }
  },
);
