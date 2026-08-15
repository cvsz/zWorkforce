const axios = require("axios");
const { PublishingProvider } = require("./publishingProvider");

const TRANSIENT_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);
const EXPIRED_SUBCODES = new Set([458, 459, 460, 463, 464, 467]);

function normalizeProviderError(error) {
  const status = Number(error?.response?.status || 0) || null;
  const source = error?.response?.data?.error || {};
  const providerCode = source.code == null ? null : String(source.code);
  const providerSubcode =
    source.error_subcode == null ? null : String(source.error_subcode);
  const tokenExpired =
    providerCode === "190" && EXPIRED_SUBCODES.has(Number(providerSubcode));
  const rateLimited = status === 429 || providerCode === "4";
  const retryable =
    !tokenExpired &&
    (Boolean(source.is_transient) ||
      rateLimited ||
      TRANSIENT_STATUS.has(status));

  return {
    name: "ProviderError",
    code: tokenExpired
      ? "AUTH_EXPIRED"
      : rateLimited
        ? "RATE_LIMITED"
        : retryable
          ? "PROVIDER_TRANSIENT"
          : "PROVIDER_REJECTED",
    message: tokenExpired
      ? "Provider credential has expired"
      : rateLimited
        ? "Provider rate limit exceeded"
        : "Provider request failed",
    status,
    providerCode,
    providerSubcode,
    retryable,
    tokenExpired,
  };
}

function rateLimitFrom(headers = {}) {
  const raw = headers["x-business-use-case-usage"];
  return raw ? { raw } : null;
}

class FacebookPublishingProvider extends PublishingProvider {
  constructor({
    http,
    apiVersion = process.env.FB_API_VERSION || "v19.0",
  } = {}) {
    super();
    this.http = http || ((request) => axios(request));
    this.baseUrl = `https://graph.facebook.com/${apiVersion}`;
  }

  capabilities() {
    return {
      text: true,
      image: true,
      video: true,
      delete: true,
      metrics: true,
    };
  }

  #credentials(credentials) {
    if (!credentials?.pageId || !credentials?.accessToken) {
      throw new Error("Facebook pageId and accessToken are required");
    }
    return {
      pageId: encodeURIComponent(credentials.pageId),
      headers: { authorization: `Bearer ${credentials.accessToken}` },
    };
  }

  async #request(request) {
    try {
      return await this.http({ timeout: 15000, ...request });
    } catch (error) {
      const normalized = normalizeProviderError(error);
      const providerError = new Error(normalized.message);
      Object.assign(providerError, normalized);
      throw providerError;
    }
  }

  async validateAuth(credentials) {
    const { pageId, headers } = this.#credentials(credentials);
    const response = await this.#request({
      method: "GET",
      url: `${this.baseUrl}/${pageId}`,
      headers,
      params: { fields: "id,name" },
    });
    return {
      valid: true,
      account: { id: response.data.id, name: response.data.name },
      rateLimit: rateLimitFrom(response.headers),
    };
  }

  async publish(credentials, publication) {
    const { pageId, headers } = this.#credentials(credentials);
    const endpoint = publication.kind === "image" ? "photos" : "feed";
    const data =
      publication.kind === "image"
        ? { url: publication.mediaUrl, message: publication.text || "" }
        : {
            message: publication.text,
            ...(publication.link ? { link: publication.link } : {}),
          };
    const response = await this.#request({
      method: "POST",
      url: `${this.baseUrl}/${pageId}/${endpoint}`,
      headers: {
        ...headers,
        "x-zeto-idempotency-key": publication.idempotencyKey,
      },
      data,
    });
    return {
      providerPublicationId: response.data.id,
      permalink: `https://www.facebook.com/${response.data.id}`,
      rateLimit: rateLimitFrom(response.headers),
    };
  }

  async delete(credentials, publicationId) {
    const { headers } = this.#credentials(credentials);
    const response = await this.#request({
      method: "DELETE",
      url: `${this.baseUrl}/${encodeURIComponent(publicationId)}`,
      headers,
    });
    return {
      deleted: response.data.success === true,
      rateLimit: rateLimitFrom(response.headers),
    };
  }

  async status(credentials, publicationId) {
    const { headers } = this.#credentials(credentials);
    const response = await this.#request({
      method: "GET",
      url: `${this.baseUrl}/${encodeURIComponent(publicationId)}`,
      headers,
      params: { fields: "id,permalink_url,created_time" },
    });
    return { ...response.data, rateLimit: rateLimitFrom(response.headers) };
  }

  async metrics(credentials, publicationId, metricNames = []) {
    const { headers } = this.#credentials(credentials);
    const response = await this.#request({
      method: "GET",
      url: `${this.baseUrl}/${encodeURIComponent(publicationId)}/insights`,
      headers,
      params: { metric: metricNames.join(",") },
    });
    return {
      metrics: response.data.data || [],
      rateLimit: rateLimitFrom(response.headers),
    };
  }
}

module.exports = { FacebookPublishingProvider, normalizeProviderError };
