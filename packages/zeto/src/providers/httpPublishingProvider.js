const axios = require("axios");
const { PublishingProvider } = require("./publishingProvider");

const TRANSIENT_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);

function numericHeader(headers, name) {
  const value = headers?.[name];
  return value == null || value === "" || !Number.isFinite(Number(value))
    ? null
    : Number(value);
}

function standardRateLimit(headers = {}) {
  const limit = numericHeader(headers, "x-rate-limit-limit");
  const remaining = numericHeader(headers, "x-rate-limit-remaining");
  const resetAt = numericHeader(headers, "x-rate-limit-reset");
  return limit == null && remaining == null && resetAt == null
    ? null
    : {
        ...(limit == null ? {} : { limit }),
        ...(remaining == null ? {} : { remaining }),
        ...(resetAt == null ? {} : { resetAt }),
      };
}

function normalizeHttpProviderError(error, provider) {
  const status = Number(error?.response?.status || 0) || null;
  const rateLimited = status === 429;
  const tokenExpired = status === 401;
  const retryable =
    !tokenExpired && (rateLimited || TRANSIENT_STATUS.has(status));
  return {
    name: "ProviderError",
    provider,
    code: tokenExpired
      ? "AUTH_EXPIRED"
      : rateLimited
        ? "RATE_LIMITED"
        : retryable
          ? "PROVIDER_TRANSIENT"
          : "PROVIDER_REJECTED",
    message: tokenExpired
      ? "Provider credential is invalid or expired"
      : rateLimited
        ? "Provider rate limit exceeded"
        : "Provider request failed",
    status,
    retryable,
    tokenExpired,
    rateLimit: standardRateLimit(error?.response?.headers),
  };
}

class HttpPublishingProvider extends PublishingProvider {
  constructor(provider, { http } = {}) {
    super();
    this.provider = provider;
    this.http = http || ((request) => axios(request));
  }

  bearer(accessToken, extra = {}) {
    if (!accessToken)
      throw new Error(`${this.provider} accessToken is required`);
    return { authorization: `Bearer ${accessToken}`, ...extra };
  }

  async request(request) {
    try {
      return await this.http({ timeout: 30000, ...request });
    } catch (error) {
      const normalized = normalizeHttpProviderError(error, this.provider);
      const providerError = new Error(normalized.message);
      Object.assign(providerError, normalized);
      throw providerError;
    }
  }
}

module.exports = {
  HttpPublishingProvider,
  normalizeHttpProviderError,
  standardRateLimit,
};
