const fs = require("node:fs/promises");

async function assertImageFile(filePath) {
  const handle = await fs.open(filePath, "r");
  try {
    const buffer = Buffer.alloc(12);
    const { bytesRead } = await handle.read(buffer, 0, buffer.length, 0);
    const bytes = buffer.subarray(0, bytesRead);
    if (bytes.subarray(0, 8).equals(Buffer.from("89504e470d0a1a0a", "hex")))
      return "image/png";
    if (bytes.subarray(0, 3).equals(Buffer.from("ffd8ff", "hex")))
      return "image/jpeg";
    if (
      bytes.subarray(0, 6).toString("ascii") === "GIF87a" ||
      bytes.subarray(0, 6).toString("ascii") === "GIF89a"
    )
      return "image/gif";
    if (
      bytes.subarray(0, 4).toString("ascii") === "RIFF" &&
      bytes.subarray(8, 12).toString("ascii") === "WEBP"
    )
      return "image/webp";
    throw new Error("File is not a supported image");
  } finally {
    await handle.close();
  }
}

module.exports = { assertImageFile };
