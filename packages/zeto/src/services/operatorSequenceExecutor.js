"use strict";

/**
 * M12 sequence step executor — spec §4.3 + §6.
 *
 * This slice ships a small set of built-in, read-only intents grounded in real
 * persisted state (queue, session, events). Unsupported intents fail loudly
 * with a visible "cannot do" message (§6.1) — never silently. The tool gateway
 * slice replaces this with the full skill/tool registry; sequences already run
 * against a stable step-execution seam.
 */

const { isKnownIntent } = require("../domain/operatorSequences");

class UnsupportedIntentError extends Error {
  constructor(intent) {
    super(
      `Unsupported intent "${intent}" — no tool registered for it. ` +
        `Supported read-only intents: queue.read, session.status, events.recent.`,
    );
    this.name = "UnsupportedIntentError";
    this.code = "UNSUPPORTED_INTENT";
  }
}

function clampLimit(raw, fallback = 25, max = 100) {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(Math.max(Math.trunc(parsed), 1), max);
}

/**
 * Execute one sequence step. `context` carries the session and repository so
 * every built-in intent reads durable state — no fabricated analytics.
 */
async function executeSequenceStep({ intent, args = {}, context }) {
  if (!isKnownIntent(intent)) throw new UnsupportedIntentError(intent);

  const { session, repository } = context;

  switch (intent) {
    case "queue.read": {
      const status = typeof args.status === "string" ? args.status : null;
      const limit = clampLimit(args.limit, 25);
      const params = [limit];
      let where = "";
      if (status) {
        params.unshift(status);
        where = "WHERE status = $1";
      }
      const result = await repository.pool.query(
        `SELECT id, status, message, created_at\n         FROM publication_queue\n         ${where}\n         ORDER BY created_at ASC\n         LIMIT $${status ? 2 : 1}`,
        params,
      );
      return {
        count: result.rowCount,
        status: status ?? "all",
        items: result.rows.map((row) => ({
          id: row.id,
          status: row.status,
          message: row.message,
          created_at: row.created_at,
        })),
      };
    }
    case "session.status": {
      return {
        id: session.id,
        state: session.state,
        mode: session.mode,
        generation: session.generation,
        last_sequence_id: session.lastSequenceId ?? 0,
      };
    }
    case "events.recent": {
      const limit = clampLimit(args.limit, 25);
      const events = await repository.listEventsAfter(session.id, 0, limit);
      return {
        count: events.length,
        items: events.map((event) => ({
          event_id: event.event_id,
          sequence_id: event.sequence_id,
          type: event.type,
          occurred_at: event.occurred_at,
        })),
      };
    }
    default:
      throw new UnsupportedIntentError(intent);
  }
}

module.exports = { executeSequenceStep, UnsupportedIntentError };
