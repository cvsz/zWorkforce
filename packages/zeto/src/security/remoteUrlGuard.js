const dns = require("node:dns").promises;
const net = require("node:net");

function ipv4Blocked(address) {
  const octets = address.split(".").map(Number);
  const [a, b] = octets;
  return (
    a === 0 ||
    a === 10 ||
    a === 127 ||
    (a === 100 && b >= 64 && b <= 127) ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 0) ||
    (a === 192 && b === 168) ||
    (a === 198 && (b === 18 || b === 19)) ||
    a >= 224
  );
}

function addressBlocked(address) {
  const family = net.isIP(address);
  if (family === 4) return ipv4Blocked(address);
  if (family !== 6) return true;
  const normalized = address.toLowerCase();
  if (normalized.startsWith("::ffff:")) {
    return addressBlocked(normalized.slice(7));
  }
  return (
    normalized === "::" ||
    normalized === "::1" ||
    normalized.startsWith("fc") ||
    normalized.startsWith("fd") ||
    /^fe[89ab]/.test(normalized)
  );
}

async function assertSafeRemoteUrl(value, { lookup = dns.lookup } = {}) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error("Remote URL is not allowed");
  }
  if (
    url.protocol !== "https:" ||
    url.username ||
    url.password ||
    url.port ||
    url.hostname.toLowerCase() === "localhost"
  ) {
    throw new Error("Remote URL is not allowed");
  }
  const literalFamily = net.isIP(url.hostname);
  const addresses = literalFamily
    ? [{ address: url.hostname, family: literalFamily }]
    : await lookup(url.hostname, { all: true, verbatim: true });
  if (
    !addresses.length ||
    addresses.some(({ address }) => addressBlocked(address))
  ) {
    throw new Error("Remote URL is not allowed");
  }
  return url;
}

module.exports = { assertSafeRemoteUrl, addressBlocked };
