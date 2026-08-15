const assert = require("node:assert/strict");
const test = require("node:test");

const { assertSafeRemoteUrl } = require("../src/security/remoteUrlGuard");

test("remote URL guard permits HTTPS hosts only when every resolved address is public", async () => {
  const url = await assertSafeRemoteUrl("https://cdn.example.com/a.png", {
    lookup: async () => [
      { address: "8.8.8.8", family: 4 },
      { address: "2606:4700:4700::1111", family: 6 },
    ],
  });
  assert.equal(url.href, "https://cdn.example.com/a.png");
});

test("remote URL guard blocks credentials, non-HTTPS, localhost, and private DNS", async () => {
  const cases = [
    [
      "http://example.com/a.png",
      async () => [{ address: "8.8.8.8", family: 4 }],
    ],
    [
      "https://user:pass@example.com/a.png",
      async () => [{ address: "8.8.8.8", family: 4 }],
    ],
    [
      "https://localhost/a.png",
      async () => [{ address: "127.0.0.1", family: 4 }],
    ],
    [
      "https://example.com/a.png",
      async () => [{ address: "10.0.0.2", family: 4 }],
    ],
    [
      "https://example.com/a.png",
      async () => [{ address: "fd00::1", family: 6 }],
    ],
  ];
  for (const [value, lookup] of cases) {
    await assert.rejects(
      () => assertSafeRemoteUrl(value, { lookup }),
      /not allowed/,
    );
  }
});
