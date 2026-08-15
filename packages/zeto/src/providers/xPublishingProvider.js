const {
  HttpPublishingProvider,
  standardRateLimit,
} = require("./httpPublishingProvider");

class XPublishingProvider extends HttpPublishingProvider {
  constructor(options = {}) {
    super("x", options);
    this.baseUrl = "https://api.x.com/2";
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

  async validateAuth(credentials) {
    const response = await this.request({
      method: "GET",
      url: `${this.baseUrl}/users/me`,
      headers: this.bearer(credentials?.accessToken),
      params: { "user.fields": "id,name,username" },
    });
    return {
      valid: true,
      account: response.data.data,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async uploadMedia(credentials, media) {
    if (!Buffer.isBuffer(media?.buffer) || !media.mimeType)
      throw new Error(
        "X media publishing requires buffered media and mimeType",
      );
    const response = await this.request({
      method: "POST",
      url: `${this.baseUrl}/media/upload`,
      headers: this.bearer(credentials?.accessToken, {
        "content-type": media.mimeType,
      }),
      params: {
        "media.category": media.mimeType.startsWith("video/")
          ? "tweet_video"
          : "tweet_image",
        media_type: media.mimeType,
      },
      data: media.buffer,
      maxBodyLength: Infinity,
    });
    return response.data.data?.id || response.data.media_id_string;
  }

  async publish(credentials, publication) {
    const mediaIds = publication.media
      ? [await this.uploadMedia(credentials, publication.media)]
      : publication.mediaIds;
    const response = await this.request({
      method: "POST",
      url: `${this.baseUrl}/tweets`,
      headers: this.bearer(credentials?.accessToken, {
        "content-type": "application/json",
      }),
      data: {
        text: publication.text,
        ...(mediaIds?.length ? { media: { media_ids: mediaIds } } : {}),
      },
    });
    const id = response.data.data?.id;
    return {
      providerPublicationId: id,
      permalink: credentials.username
        ? `https://x.com/${credentials.username}/status/${id}`
        : `https://x.com/i/web/status/${id}`,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async delete(credentials, publicationId) {
    const response = await this.request({
      method: "DELETE",
      url: `${this.baseUrl}/tweets/${encodeURIComponent(publicationId)}`,
      headers: this.bearer(credentials?.accessToken),
    });
    return {
      deleted: response.data.data?.deleted === true,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async status(credentials, publicationId) {
    const response = await this.request({
      method: "GET",
      url: `${this.baseUrl}/tweets/${encodeURIComponent(publicationId)}`,
      headers: this.bearer(credentials?.accessToken),
      params: { "tweet.fields": "created_at,public_metrics" },
    });
    return {
      publication: response.data.data,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async metrics(credentials, publicationId) {
    const result = await this.status(credentials, publicationId);
    return {
      metrics: result.publication?.public_metrics || {},
      rateLimit: result.rateLimit,
    };
  }
}

module.exports = { XPublishingProvider };
