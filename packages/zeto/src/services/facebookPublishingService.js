const fbController = require("../fbController");
const {
  FacebookPublishingProvider,
} = require("../providers/facebookPublishingProvider");
const { assertSafeRemoteUrl } = require("../security/remoteUrlGuard");

const provider = new FacebookPublishingProvider();

async function publishToFacebook(
  message,
  imageUrl,
  pageIdContext,
  idempotencyKey,
) {
  const credentials = {
    pageId: await fbController.getPageId(pageIdContext),
    accessToken: await fbController.getAccessToken(pageIdContext),
  };
  if (imageUrl) await assertSafeRemoteUrl(imageUrl);
  const result = await provider.publish(credentials, {
    kind: imageUrl ? "image" : "text",
    mediaUrl: imageUrl || undefined,
    text: message,
    idempotencyKey,
  });
  return {
    id: result.providerPublicationId,
    permalink: result.permalink,
    rateLimit: result.rateLimit,
  };
}

module.exports = { publishToFacebook };
