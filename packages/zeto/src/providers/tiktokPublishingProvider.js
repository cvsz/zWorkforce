const {
  HttpPublishingProvider,
  standardRateLimit,
} = require("./httpPublishingProvider");

class TikTokPublishingProvider extends HttpPublishingProvider {
  constructor(options = {}) {
    super("tiktok", options);
    this.baseUrl = "https://open.tiktokapis.com/v2";
  }

  capabilities() {
    return {
      text: false,
      image: false,
      video: true,
      delete: false,
      metrics: true,
    };
  }

  async creatorInfo(credentials) {
    const response = await this.request({
      method: "POST",
      url: `${this.baseUrl}/post/publish/creator_info/query/`,
      headers: this.bearer(credentials?.accessToken, {
        "content-type": "application/json; charset=UTF-8",
      }),
      data: {},
    });
    return response;
  }

  async validateAuth(credentials) {
    const response = await this.creatorInfo(credentials);
    return {
      valid: true,
      account: response.data.data,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async publish(credentials, publication) {
    if (publication.userConsent !== true)
      throw new Error("TikTok Direct Post requires explicit user consent");
    if (!publication.mediaUrl)
      throw new Error("TikTok publishing requires a verified mediaUrl");
    const creator = await this.creatorInfo(credentials);
    const options = creator.data.data?.privacy_level_options || [];
    if (!options.includes(publication.privacyLevel))
      throw new Error("TikTok privacy level is not available for this creator");
    const response = await this.request({
      method: "POST",
      url: `${this.baseUrl}/post/publish/video/init/`,
      headers: this.bearer(credentials.accessToken, {
        "content-type": "application/json; charset=UTF-8",
      }),
      data: {
        post_info: {
          title: publication.text || "",
          privacy_level: publication.privacyLevel,
          disable_duet: Boolean(publication.disableDuet),
          disable_comment: Boolean(publication.disableComment),
          disable_stitch: Boolean(publication.disableStitch),
          video_cover_timestamp_ms: publication.coverTimestampMs || 1000,
        },
        source_info: {
          source: "PULL_FROM_URL",
          video_url: publication.mediaUrl,
        },
      },
    });
    return {
      providerPublicationId: response.data.data?.publish_id,
      permalink: null,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async delete() {
    const error = new Error(
      "TikTok publication deletion is not supported by this adapter",
    );
    error.code = "CAPABILITY_UNSUPPORTED";
    throw error;
  }

  async status(credentials, publicationId) {
    const response = await this.request({
      method: "POST",
      url: `${this.baseUrl}/post/publish/status/fetch/`,
      headers: this.bearer(credentials?.accessToken, {
        "content-type": "application/json; charset=UTF-8",
      }),
      data: { publish_id: publicationId },
    });
    return {
      publication: response.data.data,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async metrics(credentials, publicationId) {
    const response = await this.request({
      method: "POST",
      url: `${this.baseUrl}/video/query/`,
      headers: this.bearer(credentials?.accessToken, {
        "content-type": "application/json",
      }),
      params: { fields: "id,like_count,comment_count,share_count,view_count" },
      data: { filters: { video_ids: [publicationId] } },
    });
    return {
      metrics: response.data.data?.videos?.[0] || {},
      rateLimit: standardRateLimit(response.headers),
    };
  }
}

module.exports = { TikTokPublishingProvider };
