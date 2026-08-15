function label(value) {
  return String(value)
    .replaceAll("\\", "\\\\")
    .replaceAll("\n", "\\n")
    .replaceAll('"', '\\"');
}

class MetricsRegistry {
  constructor() {
    this.http = new Map();
  }

  observeHttp(method, route, status, seconds) {
    const key = JSON.stringify([method, route, String(status)]);
    const value = this.http.get(key) || { count: 0, sum: 0 };
    value.count += 1;
    value.sum += seconds;
    this.http.set(key, value);
  }

  render(snapshot = {}) {
    const lines = [
      "# HELP zeto_http_requests_total Total HTTP requests.",
      "# TYPE zeto_http_requests_total counter",
      "# HELP zeto_http_request_duration_seconds HTTP request duration.",
      "# TYPE zeto_http_request_duration_seconds summary",
    ];
    for (const [key, value] of [...this.http.entries()].sort()) {
      const [method, route, status] = JSON.parse(key);
      const labels = `method="${label(method)}",route="${label(route)}",status="${label(status)}"`;
      lines.push(`zeto_http_requests_total{${labels}} ${value.count}`);
      lines.push(
        `zeto_http_request_duration_seconds_sum{${labels}} ${value.sum}`,
      );
      lines.push(
        `zeto_http_request_duration_seconds_count{${labels}} ${value.count}`,
      );
    }
    for (const [name, statuses] of [
      ["jobs", snapshot.jobs],
      ["publications", snapshot.publications],
      ["approvals", snapshot.approvals],
    ]) {
      for (const [status, count] of Object.entries(statuses || {}).sort()) {
        lines.push(`zeto_${name}{status="${label(status)}"} ${Number(count)}`);
      }
    }
    lines.push(
      `zeto_provider_failures_total ${Number(snapshot.providerFailures || 0)}`,
    );
    lines.push(
      `zeto_generation_cost_total ${Number(snapshot.generationCost || 0)}`,
    );
    return `${lines.join("\n")}\n`;
  }
}

async function collectOperationalMetrics(pool) {
  const [jobs, publications, approvals, providers, costs] = await Promise.all([
    pool.query(
      "SELECT status, count(*)::bigint AS count FROM jobs GROUP BY status",
    ),
    pool.query(
      "SELECT status, count(*)::bigint AS count FROM publications GROUP BY status",
    ),
    pool.query(
      "SELECT decision AS status, count(*)::bigint AS count FROM approvals GROUP BY decision",
    ),
    pool.query(
      "SELECT count(*)::bigint AS count FROM publications WHERE status = 'failed'",
    ),
    pool.query(
      "SELECT COALESCE(sum(estimated_cost), 0) AS total FROM cost_events",
    ),
  ]);
  const grouped = (result) =>
    Object.fromEntries(
      result.rows.map((row) => [row.status, Number(row.count)]),
    );
  return {
    jobs: grouped(jobs),
    publications: grouped(publications),
    approvals: grouped(approvals),
    providerFailures: Number(providers.rows[0].count),
    generationCost: Number(costs.rows[0].total),
  };
}

module.exports = { MetricsRegistry, collectOperationalMetrics };
