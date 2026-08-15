const { FacebookPublishingProvider } = require("./facebookPublishingProvider");
const {
  InstagramPublishingProvider,
} = require("./instagramPublishingProvider");
const { YouTubePublishingProvider } = require("./youtubePublishingProvider");
const { TikTokPublishingProvider } = require("./tiktokPublishingProvider");
const { XPublishingProvider } = require("./xPublishingProvider");
const { LinkedInPublishingProvider } = require("./linkedinPublishingProvider");

class ProviderRegistry {
  constructor(providers = {}) {
    this.providers = new Map();
    for (const [name, provider] of Object.entries(providers))
      this.register(name, provider);
  }

  register(name, provider) {
    const key = String(name).toLowerCase();
    if (!key || !provider || typeof provider.capabilities !== "function")
      throw new Error(
        "A named publishing provider with capabilities is required",
      );
    if (this.providers.has(key))
      throw new Error(`Publishing provider already registered: ${key}`);
    this.providers.set(key, provider);
    return this;
  }

  get(name) {
    const key = String(name || "").toLowerCase();
    const provider = this.providers.get(key);
    if (!provider)
      throw new Error(`Unknown publishing provider: ${key || "<empty>"}`);
    return provider;
  }

  list() {
    return [...this.providers.entries()].map(([name, provider]) => ({
      name,
      capabilities: provider.capabilities(),
    }));
  }

  validatePublication(name, publication) {
    const provider = this.get(name);
    const kind = publication?.kind || "text";
    if (!provider.capabilities()[kind])
      throw new Error(`${name} does not support ${kind} publications`);
    return provider;
  }
}

function createDefaultProviderRegistry(options = {}) {
  return new ProviderRegistry({
    facebook: new FacebookPublishingProvider(options.facebook),
    instagram: new InstagramPublishingProvider(options.instagram),
    youtube: new YouTubePublishingProvider(options.youtube),
    tiktok: new TikTokPublishingProvider(options.tiktok),
    x: new XPublishingProvider(options.x),
    linkedin: new LinkedInPublishingProvider(options.linkedin),
  });
}

module.exports = { ProviderRegistry, createDefaultProviderRegistry };
