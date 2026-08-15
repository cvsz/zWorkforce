function retryDecision({
  attempt,
  maxAttempts,
  baseMs = 1000,
  maxMs = 300000,
  random = Math.random,
}) {
  if (
    !Number.isInteger(attempt) ||
    !Number.isInteger(maxAttempts) ||
    attempt < 1 ||
    maxAttempts < 1
  ) {
    throw new Error("attempt and maxAttempts must be positive integers");
  }
  if (attempt >= maxAttempts) return { retry: false, delayMs: null };
  const exponential = Math.min(maxMs, baseMs * 2 ** (attempt - 1));
  const jittered = Math.round(exponential * (0.5 + random()));
  return { retry: true, delayMs: Math.min(maxMs, jittered) };
}

module.exports = { retryDecision };
