const fs = require("node:fs");

function readSecret(name, { env = process.env, maxBytes = 65536 } = {}) {
  const file = env[`${name}_FILE`];
  if (!file) return env[name] || undefined;
  const stat = fs.statSync(file);
  if (!stat.isFile() || stat.size > maxBytes) {
    throw new Error(`${name}_FILE is not a valid secret file`);
  }
  const value = fs.readFileSync(file, "utf8").trim();
  if (!value || value.includes("\0"))
    throw new Error(`${name}_FILE is empty or invalid`);
  return value;
}

module.exports = { readSecret };
