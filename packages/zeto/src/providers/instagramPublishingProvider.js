const {
  HttpPublishingProvider,
  standardRateLimit,
} = require("./httpPublishingProvider");

class InstagramPublishingProvider extends HttpPublishingProvider {
  constructor({
    apiVersion = process.env.META_API_VERSION || "v23.0",
    ...options
  } = {}) {
    super("instagram", options);
    this.baseUrl = `https://graph.facebook.com/${apiVersion}`;
  }

  capabilities() {
    return {
      text: false,
      image: true,
      video: true,
      delete: false,
      metrics: true,
    };
  }

  credentials(credentials) {
    if (!credentials?.accountId)
      throw new Error("Instagram accountId is required");
    return {
      accountId: encodeURIComponent(credentials.accountId),
      headers: this.bearer(credentials.accessToken),
    };
  }

  async validateAuth(credentials) {
    const { accountId, headers } = this.credentials(credentials);
    const response = await this.request({
      method: "GET",
      url: `${this.baseUrl}/${accountId}`,
      headers,
      params: { fields: "id,username" },
    });
    return {
      valid: true,
      account: response.data,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async publish(credentials, publication) {
    const { accountId, headers } = this.credentials(credentials);
    if (!publication.mediaUrl)
      throw new Error("Instagram publishing requires mediaUrl");
    const isVideo = publication.kind === "video";
    const created = await this.request({
      method: "POST",
      url: `${this.baseUrl}/${accountId}/media`,
      headers,
      data: {
        ...(isVideo
          ? {
              media_type: publication.mediaType || "REELS",
              video_url: publication.mediaUrl,
            }
          : { image_url: publication.mediaUrl }),
        caption: publication.text || "",
      },
    });
    const response = await this.request({
      method: "POST",
      url: `${this.baseUrl}/${accountId}/media_publish`,
      headers,
      data: { creation_id: created.data.id },
    });
    return {
      providerPublicationId: response.data.id,
      permalink: `https://www.instagram.com/p/${response.data.id}/`,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async delete() {
    const error = new Error(
      "Instagram publication deletion is not supported by this adapter",
    );
    error.code = "CAPABILITY_UNSUPPORTED";
    throw error;
  }

  async status(credentials, publicationId) {
    const { headers } = this.credentials(credentials);
    const response = await this.request({
      method: "GET",
      url: `${this.baseUrl}/${encodeURIComponent(publicationId)}`,
      headers,
      params: { fields: "id,status_code,permalink,timestamp" },
    });
    return { ...response.data, rateLimit: standardRateLimit(response.headers) };
  }

  async metrics(credentials, publicationId, metricNames = []) {
    const { headers } = this.credentials(credentials);
    const response = await this.request({
      method: "GET",
      url: `${this.baseUrl}/${encodeURIComponent(publicationId)}/insights`,
      headers,
      params: { metric: metricNames.join(",") },
    });
    return {
      metrics: response.data.data || [],
      rateLimit: standardRateLimit(response.headers),
    };
  }
}

module.exports = { InstagramPublishingProvider };
