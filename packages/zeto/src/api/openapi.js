const document = {
  openapi: "3.1.0",
  info: { title: "Zeto API", version: "2.0.0-alpha.1" },
  paths: {
    "/v1/providers": {
      get: {
        summary: "List publishing providers and capabilities",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Provider capabilities" } },
      },
    },
    "/v1/factory-runs": {
      post: {
        summary: "Start or replay the canonical M01-M10 content factory",
        security: [{ bearerAuth: [] }],
        parameters: [
          {
            name: "Idempotency-Key",
            in: "header",
            required: true,
            schema: { type: "string" },
          },
        ],
        responses: {
          202: {
            description: "Run accepted and processed to completion or approval",
          },
          422: { description: "Validation error" },
        },
      },
    },
    "/v1/factory-runs/{runId}/approve": {
      post: {
        summary: "Approve and resume a paused factory run",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Run resumed" } },
      },
    },
    "/v1/brands": {
      get: {
        summary: "List brands",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Brands" } },
      },
      post: {
        summary: "Create a brand",
        security: [{ bearerAuth: [] }],
        parameters: [
          {
            name: "Idempotency-Key",
            in: "header",
            required: true,
            schema: { type: "string" },
          },
        ],
        responses: {
          201: { description: "Created" },
          422: { description: "Validation error" },
        },
      },
    },
    "/v1/workflows": {
      post: {
        summary: "Create a workflow definition",
        security: [{ bearerAuth: [] }],
        responses: {
          201: { description: "Created" },
          422: { description: "Validation error" },
        },
      },
    },
    "/v1/workflows/{workflowId}/runs": {
      post: {
        summary: "Start or replay an idempotent workflow run",
        security: [{ bearerAuth: [] }],
        parameters: [
          {
            name: "workflowId",
            in: "path",
            required: true,
            schema: { type: "string", format: "uuid" },
          },
          {
            name: "Idempotency-Key",
            in: "header",
            required: true,
            schema: { type: "string" },
          },
        ],
        responses: { 202: { description: "Accepted" } },
      },
    },
    "/v1/workflow-runs/{runId}": {
      get: {
        summary: "Inspect a workflow run and its steps",
        security: [{ bearerAuth: [] }],
        responses: {
          200: { description: "Workflow run" },
          404: { description: "Not found" },
        },
      },
    },
    "/v1/workflow-runs": {
      get: {
        summary: "List recent workflow runs for a brand",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Workflow runs" } },
      },
    },
    "/v1/workflow-runs/{runId}/cancel": {
      post: {
        summary: "Cancel a workflow run",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Cancelled" } },
      },
    },
    "/v1/metrics": {
      post: {
        summary: "Ingest validated daily provider metrics",
        security: [{ bearerAuth: [] }],
        responses: {
          201: { description: "Stored" },
          422: { description: "Validation error" },
        },
      },
    },
    "/v1/analytics/control-room": {
      get: {
        summary: "Read current and prior-period control room metrics",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Analytics report" } },
      },
    },
    "/v1/mentions": {
      post: {
        summary: "Ingest and classify a social mention",
        security: [{ bearerAuth: [] }],
        responses: {
          201: { description: "Mention and escalation" },
          422: { description: "Validation error" },
        },
      },
    },
    "/v1/operator/sessions": {
      post: {
        summary: "Create a Z.A.R.V.I.S. operator session (IDLE, generation 1)",
        security: [{ bearerAuth: [] }],
        responses: {
          201: { description: "Session created" },
          422: { description: "Validation error" },
        },
      },
    },
    "/v1/operator/sessions/{id}": {
      get: {
        summary:
          "Fetch an operator session snapshot (state, generation, checkpoint)",
        security: [{ bearerAuth: [] }],
        parameters: [
          {
            name: "id",
            in: "path",
            required: true,
            schema: { type: "string", format: "uuid" },
          },
        ],
        responses: {
          200: { description: "Session snapshot" },
          404: { description: "Not found" },
        },
      },
    },
    "/v1/operator/sessions/{id}/events": {
      get: {
        summary:
          "SSE event stream; resumable via Last-Event-ID (replays sequence_id > last in order)",
        security: [{ bearerAuth: [] }],
        parameters: [
          {
            name: "id",
            in: "path",
            required: true,
            schema: { type: "string", format: "uuid" },
          },
          {
            name: "Last-Event-ID",
            in: "header",
            schema: { type: "integer", minimum: 0, default: 0 },
          },
        ],
        responses: { 200: { description: "Event stream" } },
      },
    },
    "/v1/operator/sessions/{id}/commands": {
      post: {
        summary: "Submit a text/voice/sequence command",
        security: [{ bearerAuth: [] }],
        responses: {
          201: { description: "Command received" },
          422: { description: "Validation error" },
        },
      },
    },
    "/v1/operator/sessions/{id}/cancel": {
      post: {
        summary: "Cancel a session (ordinary, non-emergency)",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Cancelling" } },
      },
    },
    "/v1/operator/sessions/{id}/pause": {
      post: {
        summary: "Pause a session (deterministic per-state policy)",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Pause applied or deferred" } },
      },
    },
    "/v1/operator/sessions/{id}/resume": {
      post: {
        summary: "Resume a paused session through re-authorization + recovery",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Resumed" } },
      },
    },
    "/v1/operator/sessions/{id}/emergency-stop": {
      post: {
        summary:
          "Emergency stop (admin): terminal EMERGENCY_STOPPED, kill switch latched",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Stopped" } },
      },
    },
    "/v1/operator/plans/{id}": {
      get: {
        summary: "Inspect an operator plan and its steps",
        security: [{ bearerAuth: [] }],
        responses: {
          200: { description: "Plan" },
          404: { description: "Not found" },
        },
      },
    },
    "/v1/operator/plans/{id}/approve": {
      post: {
        summary: "Approve a pending plan (AWAITING_APPROVAL → EXECUTING)",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Approved" } },
      },
    },
    "/v1/operator/plans/{id}/reject": {
      post: {
        summary: "Reject a pending plan (AWAITING_APPROVAL → CANCELLED)",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Rejected" } },
      },
    },
    "/v1/operator/sequences": {
      get: {
        summary: "List saved operator sequences (§4.3)",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Sequence list" } },
      },
      post: {
        summary: "Save an operator sequence (name, mode, ordered steps)",
        security: [{ bearerAuth: [] }],
        responses: {
          201: { description: "Sequence created" },
          422: { description: "Validation error" },
        },
      },
    },
    "/v1/operator/sequences/{id}": {
      get: {
        summary: "Fetch a sequence with its ordered steps",
        security: [{ bearerAuth: [] }],
        parameters: [
          {
            name: "id",
            in: "path",
            required: true,
            schema: { type: "string", format: "uuid" },
          },
        ],
        responses: {
          200: { description: "Sequence" },
          404: { description: "Not found" },
        },
      },
      put: {
        summary: "Update a sequence (save/reorder steps)",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Updated" } },
      },
      delete: {
        summary: "Delete a sequence",
        security: [{ bearerAuth: [] }],
        responses: { 200: { description: "Deleted" } },
      },
    },
    "/v1/operator/sequences/{id}/run": {
      post: {
        summary:
          "Run or dry-run a sequence; resume a failed run (high-risk replay requires confirm_replay)",
        security: [{ bearerAuth: [] }],
        parameters: [
          {
            name: "id",
            in: "path",
            required: true,
            schema: { type: "string", format: "uuid" },
          },
        ],
        responses: {
          201: { description: "Run started; { run_id }" },
          409: { description: "Confirmation required for high-risk replay" },
        },
      },
    },
    "/v1/operator/sequence-runs/{id}": {
      get: {
        summary: "Inspect a sequence run and per-step results",
        security: [{ bearerAuth: [] }],
        parameters: [
          {
            name: "id",
            in: "path",
            required: true,
            schema: { type: "string", format: "uuid" },
          },
        ],
        responses: {
          200: { description: "Run with steps" },
          404: { description: "Not found" },
        },
      },
    },
  },
  components: {
    securitySchemes: { bearerAuth: { type: "http", scheme: "bearer" } },
  },
};

module.exports = { openApiDocument: document };
