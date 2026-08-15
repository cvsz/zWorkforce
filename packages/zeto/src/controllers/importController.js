const fs = require("fs");
const readline = require("readline");
const db = require("../db");

const importPosts = async (req, res) => {
  if (!req.file) {
    return res.status(400).json({
      ok: false,
      error: { code: "MISSING_FILE", message: "CSV file is required" },
    });
  }

  const results = [];
  const errors = [];
  const fileStream = fs.createReadStream(req.file.path);
  const rl = readline.createInterface({
    input: fileStream,
    crlfDelay: Infinity,
  });

  let isHeader = true;
  let lineNum = 0;

  for await (const line of rl) {
    lineNum++;
    if (isHeader) {
      isHeader = false;
      continue;
    }

    // Basic CSV parsing: message,imageUrl,scheduledAt
    const [message, imageUrl, scheduledAt] = line
      .split(",")
      .map((s) => s.trim());

    if (!message) {
      errors.push({ line: lineNum, message: "Message is missing" });
      continue;
    }

    const entry = await db.queue.add({
      message,
      imageUrl: imageUrl || null,
      scheduledAt: scheduledAt || null,
      type: imageUrl ? "photo" : "text",
      status: "pending",
      pageId: req.headers?.["x-page-id"] || "default",
    });
    results.push(entry);
  }

  // Clean up
  fs.unlinkSync(req.file.path);

  return res.status(200).json({ ok: true, imported: results.length, errors });
};

module.exports = { importPosts };
