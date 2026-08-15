const {
  HttpPublishingProvider,
  standardRateLimit,
} = require("./httpPublishingProvider");

class LinkedInPublishingProvider extends HttpPublishingProvider {
  constructor({
    linkedinVersion = process.env.LINKEDIN_VERSION || "202606",
    ...options
  } = {}) {
    super("linkedin", options);
    this.baseUrl = "https://api.linkedin.com/rest";
    this.linkedinVersion = linkedinVersion;
  }

  capabilities() {
    return {
      text: true,
      image: true,
      video: false,
      delete: true,
      metrics: true,
    };
  }

  headers(accessToken, extra = {}) {
    return this.bearer(accessToken, {
      "X-Restli-Protocol-Version": "2.0.0",
      "Linkedin-Version": this.linkedinVersion,
      ...extra,
    });
  }

  credentials(credentials) {
    if (!credentials?.authorUrn)
      throw new Error("LinkedIn authorUrn is required");
    return {
      authorUrn: credentials.authorUrn,
      headers: this.headers(credentials.accessToken),
    };
  }

  async validateAuth(credentials) {
    const response = await this.request({
      method: "GET",
      url: "https://api.linkedin.com/v2/userinfo",
      headers: this.bearer(credentials?.accessToken),
    });
    return {
      valid: true,
      account: response.data,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async uploadImage(credentials, media) {
    if (!Buffer.isBuffer(media?.buffer) || !media.mimeType)
      throw new Error(
        "LinkedIn image publishing requires buffered media and mimeType",
      );
    const { authorUrn, headers } = this.credentials(credentials);
    const initialized = await this.request({
      method: "POST",
      url: `${this.baseUrl}/images?action=initializeUpload`,
      headers: { ...headers, "content-type": "application/json" },
      data: { initializeUploadRequest: { owner: authorUrn } },
    });
    const value = initialized.data.value;
    if (!value?.uploadUrl || !value?.image)
      throw new Error("LinkedIn did not return image upload details");
    await this.request({
      method: "PUT",
      url: value.uploadUrl,
      headers: {
        authorization: `Bearer ${credentials.accessToken}`,
        "content-type": media.mimeType,
      },
      data: media.buffer,
      maxBodyLength: Infinity,
    });
    return value.image;
  }

  async publish(credentials, publication) {
    const { authorUrn, headers } = this.credentials(credentials);
    const image = publication.media
      ? await this.uploadImage(credentials, publication.media)
      : null;
    const response = await this.request({
      method: "POST",
      url: `${this.baseUrl}/posts`,
      headers: { ...headers, "content-type": "application/json" },
      data: {
        author: authorUrn,
        commentary: publication.text || "",
        visibility: publication.visibility || "PUBLIC",
        distribution: {
          feedDistribution: "MAIN_FEED",
          targetEntities: [],
          thirdPartyDistributionChannels: [],
        },
        lifecycleState: "PUBLISHED",
        ...(image ? { content: { media: { id: image } } } : {}),
      },
    });
    const id = response.headers?.["x-restli-id"] || response.data.id;
    return {
      providerPublicationId: id,
      permalink: id ? `https://www.linkedin.com/feed/update/${id}` : null,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async delete(credentials, publicationId) {
    const response = await this.request({
      method: "DELETE",
      url: `${this.baseUrl}/posts/${encodeURIComponent(publicationId)}`,
      headers: this.headers(credentials?.accessToken),
    });
    return {
      deleted: response.status === 204 || response.status === 200,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async status(credentials, publicationId) {
    const response = await this.request({
      method: "GET",
      url: `${this.baseUrl}/posts/${encodeURIComponent(publicationId)}`,
      headers: this.headers(credentials?.accessToken),
    });
    return {
      publication: response.data,
      rateLimit: standardRateLimit(response.headers),
    };
  }

  async metrics(credentials, publicationId) {
    const response = await this.request({
      method: "GET",
      url: `${this.baseUrl}/socialActions/${encodeURIComponent(publicationId)}`,
      headers: this.headers(credentials?.accessToken),
    });
    return {
      metrics: response.data,
      rateLimit: standardRateLimit(response.headers),
    };
  }
}

module.exports = { LinkedInPublishingProvider };
