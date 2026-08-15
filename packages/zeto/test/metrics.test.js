const assert = require("node:assert/strict");
const test = require("node:test");

const { MetricsRegistry } = require("../src/observability/metrics");

test("metrics registry renders bounded Prometheus counters and histograms", () => {
  const metrics = new MetricsRegistry();
  metrics.observeHttp("GET", "/ready", 200, 0.125);
  metrics.observeHttp("GET", "/ready", 503, 0.25);
  const output = metrics.render({
    jobs: { queued: 2, failed: 1 },
    publications: { published: 3 },
    approvals: { approved: 4 },
    providerFailures: 1,
    generationCost: 1.25,
  });
  assert.match(
    output,
    /zeto_http_requests_total\{method="GET",route="\/ready",status="200"\} 1/,
  );
  assert.match(output, /zeto_jobs\{status="queued"\} 2/);
  assert.match(output, /zeto_generation_cost_total 1.25/);
  assert.equal(output.includes("secret"), false);
});
