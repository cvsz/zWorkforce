const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { assertImageFile } = require("../src/security/uploadValidation");

test("upload validation accepts supported image signatures and rejects spoofed files", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "zeto-upload-"));
  const png = path.join(directory, "valid.png");
  const spoofed = path.join(directory, "spoofed.png");
  await fs.writeFile(png, Buffer.from("89504e470d0a1a0a0000000d", "hex"));
  await fs.writeFile(spoofed, "not an image");
  assert.equal(await assertImageFile(png), "image/png");
  await assert.rejects(() => assertImageFile(spoofed), /supported image/);
  await fs.rm(directory, { recursive: true });
});
