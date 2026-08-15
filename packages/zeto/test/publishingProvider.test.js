const assert = require("node:assert/strict");
const test = require("node:test");

const {
  FacebookPublishingProvider,
  normalizeProviderError,
} = require("../src/providers/facebookPublishingProvider");

test("Facebook provider validates credentials and exposes capabilities", async () => {
  const calls = [];
  const provider = new FacebookPublishingProvider({
    apiVersion: "v99.0",
    http: async (request) => {
      calls.push(request);
      return { data: { id: "page-1", name: "zato" }, headers: {} };
    },
  });

  const result = await provider.validateAuth({
    pageId: "page-1",
    accessToken: "secret",
  });

  assert.equal(result.valid, true);
  assert.equal(result.account.id, "page-1");
  assert.equal(calls[0].url, "https://graph.facebook.com/v99.0/page-1");
  assert.equal(calls[0].url.includes("secret"), false);
  assert.equal(calls[0].params?.access_token, undefined);
  assert.deepEqual(provider.capabilities(), {
    text: true,
    image: true,
    video: true,
    delete: true,
    metrics: true,
  });
});

test("Facebook provider publishes idempotently shaped requests without leaking tokens", async () => {
  const calls = [];
  const provider = new FacebookPublishingProvider({
    http: async (request) => {
      calls.push(request);
      return {
        data: { id: "page-1_42" },
        headers: { "x-business-use-case-usage": '{"page-1":[]}' },
      };
    },
  });

  const result = await provider.publish(
    { pageId: "page-1", accessToken: "secret" },
    { kind: "text", text: "hello", idempotencyKey: "publication-42" },
  );

  assert.equal(calls[0].method, "POST");
  assert.equal(calls[0].data.message, "hello");
  assert.equal(calls[0].headers.authorization, "Bearer secret");
  assert.equal(calls[0].headers["x-zeto-idempotency-key"], "publication-42");
  assert.deepEqual(result, {
    providerPublicationId: "page-1_42",
    permalink: "https://www.facebook.com/page-1_42",
    rateLimit: { raw: '{"page-1":[]}' },
  });
});

test("provider errors are normalized with retry and token-expiry diagnostics", () => {
  const error = normalizeProviderError({
    response: {
      status: 401,
      data: {
        error: {
          code: 190,
          error_subcode: 463,
          message: "expired token containing secret-token",
          is_transient: false,
        },
      },
      headers: {},
    },
  });

  assert.equal(error.code, "AUTH_EXPIRED");
  assert.equal(error.retryable, false);
  assert.equal(error.tokenExpired, true);
  assert.equal(error.status, 401);
  assert.equal(error.message.includes("secret-token"), false);
});
