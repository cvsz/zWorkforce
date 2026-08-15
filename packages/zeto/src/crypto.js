const crypto = require("crypto");
const { readSecret } = require("./security/secrets");

const ALGORITHM = "aes-256-gcm";
const IV_LENGTH = 12; // 96 bits for GCM
const KEY_LENGTH = 32;
const ITERATIONS = 100000;
const DIGEST = "sha256";

// Derive encryption key from a secret string
const getEncryptionKey = () => {
  const secret =
    readSecret("SECRET_ENCRYPTION_KEY") || readSecret("FACEBOOK_APP_SECRET");

  if (!secret && process.env.NODE_ENV === "production") {
    throw new Error("SECRET_ENCRYPTION_KEY is required in production");
  }
  if (process.env.NODE_ENV === "production" && secret.length < 32) {
    throw new Error(
      "SECRET_ENCRYPTION_KEY must contain at least 32 characters",
    );
  }

  // Derive a strong 256-bit key using PBKDF2 with a fixed salt for deterministic key recovery
  return crypto.pbkdf2Sync(
    secret || "zeto-development-only-key",
    "zeto-credential-v1",
    ITERATIONS,
    KEY_LENGTH,
    DIGEST,
  );
};

const derivedKey = getEncryptionKey();

/**
 * Encrypt a text string into an AES-256-GCM cipher string
 * Format: iv_hex:auth_tag_hex:encrypted_text_hex
 */
const encrypt = (text) => {
  if (!text) return text;
  // If already encrypted, skip
  if (typeof text === "string" && text.split(":").length === 3) {
    return text;
  }
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, derivedKey, iv);

  let encrypted = cipher.update(text, "utf8", "hex");
  encrypted += cipher.final("hex");

  const authTag = cipher.getAuthTag().toString("hex");

  return `${iv.toString("hex")}:${authTag}:${encrypted}`;
};

/**
 * Decrypt an AES-256-GCM cipher string back into text
 */
const decrypt = (encryptedText) => {
  if (!encryptedText || typeof encryptedText !== "string") return encryptedText;

  // If the format doesn't match iv:authTag:encryptedText, return as is (support old unencrypted tokens)
  const parts = encryptedText.split(":");
  if (parts.length !== 3) {
    return encryptedText;
  }

  try {
    const [ivHex, authTagHex, encryptedHex] = parts;
    const iv = Buffer.from(ivHex, "hex");
    const authTag = Buffer.from(authTagHex, "hex");

    const decipher = crypto.createDecipheriv(ALGORITHM, derivedKey, iv);
    decipher.setAuthTag(authTag);

    let decrypted = decipher.update(encryptedHex, "hex", "utf8");
    decrypted += decipher.final("utf8");

    return decrypted;
  } catch {
    // Return as is if decryption fails (e.g. key changed or was not encrypted)
    return encryptedText;
  }
};

module.exports = {
  encrypt,
  decrypt,
};
