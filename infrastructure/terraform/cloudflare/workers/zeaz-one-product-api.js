const PRODUCT_PATH = "/v1/products/zeaz-one";
const PRODUCT_SOURCE = "https://one.zeaz.dev/product.json";

const corsHeaders = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, HEAD, OPTIONS",
  "access-control-allow-headers": "content-type",
  "access-control-max-age": "86400",
};

function jsonResponse(body, status, method, extraHeaders = {}) {
  const payload = JSON.stringify(body, null, 2);
  return new Response(method === "HEAD" ? null : payload, {
    status,
    headers: {
      ...corsHeaders,
      "cache-control": "public, max-age=300",
      "content-type": "application/json; charset=utf-8",
      "referrer-policy": "no-referrer",
      "x-content-type-options": "nosniff",
      ...extraHeaders,
    },
  });
}

export default {
  async fetch(request) {
    const method = request.method;
    const url = new URL(request.url);

    if (method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    if (!url.pathname.startsWith(PRODUCT_PATH)) {
      return jsonResponse({ error: "not_found", path: url.pathname }, 404, method);
    }

    if (method !== "GET" && method !== "HEAD") {
      return jsonResponse(
        { error: "method_not_allowed" },
        405,
        method,
        { allow: "GET, HEAD, OPTIONS" },
      );
    }

    const upstream = await fetch(PRODUCT_SOURCE, {
      cf: { cacheEverything: true, cacheTtl: 300 },
      headers: { accept: "application/json" },
    });

    if (!upstream.ok) {
      return jsonResponse({ error: "product_source_unavailable" }, 503, method);
    }

    const product = await upstream.json();
    return jsonResponse(product, 200, method);
  },
};
