const { performance } = require("node:perf_hooks");

async function main() {
  const url = process.env.LOAD_URL || "http://127.0.0.1:5000/ready";
  const durationMs = Number(process.env.LOAD_DURATION_MS || 10000);
  const concurrency = Number(process.env.LOAD_CONCURRENCY || 20);
  const maxP95Ms = Number(process.env.LOAD_MAX_P95_MS || 500);
  if (
    ![durationMs, concurrency, maxP95Ms].every(Number.isFinite) ||
    durationMs < 1000 ||
    concurrency < 1
  ) {
    throw new Error("Invalid load baseline configuration");
  }
  const deadline = performance.now() + durationMs;
  const latencies = [];
  let errors = 0;
  async function worker() {
    while (performance.now() < deadline) {
      const started = performance.now();
      try {
        const response = await fetch(url, {
          signal: AbortSignal.timeout(5000),
        });
        if (!response.ok) errors += 1;
        await response.arrayBuffer();
      } catch {
        errors += 1;
      } finally {
        latencies.push(performance.now() - started);
      }
    }
  }
  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  latencies.sort((a, b) => a - b);
  const percentile = (fraction) =>
    latencies[
      Math.min(latencies.length - 1, Math.floor(latencies.length * fraction))
    ];
  const result = {
    url,
    durationMs,
    concurrency,
    requests: latencies.length,
    errors,
    requestsPerSecond: Number(
      (latencies.length / (durationMs / 1000)).toFixed(2),
    ),
    p50Ms: Number(percentile(0.5).toFixed(2)),
    p95Ms: Number(percentile(0.95).toFixed(2)),
    p99Ms: Number(percentile(0.99).toFixed(2)),
  };
  console.log(JSON.stringify(result));
  if (errors || result.p95Ms > maxP95Ms) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
