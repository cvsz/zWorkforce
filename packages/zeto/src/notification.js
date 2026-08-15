const axios = require("axios");
const db = require("./db");
const { readSecret } = require("./security/secrets");
const { assertSafeRemoteUrl } = require("./security/remoteUrlGuard");

/**
 * Send a notification payload to Line Notify or Discord webhook.
 */
async function sendNotification(message, imageUrl = null) {
  const settings = await db.settings.get();

  // 1. Line Notify Webhook
  const lineToken = readSecret("LINE_NOTIFY_TOKEN") || settings.lineNotifyToken;
  if (lineToken) {
    try {
      const FormData = require("form-data");
      const form = new FormData();
      form.append("message", message);
      if (imageUrl && !imageUrl.startsWith("data:")) {
        form.append("imageThumbnail", imageUrl);
        form.append("imageFullsize", imageUrl);
      }

      await axios.post("https://notify-api.line.me/api/notify", form, {
        headers: {
          ...form.getHeaders(),
          Authorization: `Bearer ${lineToken}`,
        },
        timeout: 10000,
      });
      console.log("[notification] Line Notify notification sent successfully.");
    } catch (e) {
      console.error("[notification] Line Notify sending failed:", e.message);
    }
  }

  // 2. Discord Webhook
  const discordWebhookUrl =
    readSecret("DISCORD_WEBHOOK_URL") || settings.discordWebhookUrl;
  if (discordWebhookUrl) {
    try {
      await assertSafeRemoteUrl(discordWebhookUrl);
      const payload = {
        content: message,
      };
      if (imageUrl && !imageUrl.startsWith("data:")) {
        payload.embeds = [
          {
            image: { url: imageUrl },
          },
        ];
      }

      await axios.post(discordWebhookUrl, payload, {
        headers: { "Content-Type": "application/json" },
        timeout: 10000,
      });
      console.log("[notification] Discord webhook sent successfully.");
    } catch (e) {
      console.error(
        "[notification] Discord webhook sending failed:",
        e.message,
      );
    }
  }
}

module.exports = {
  sendNotification,
};
