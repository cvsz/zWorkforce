Continue implementing the repository until the complete CLI-to-API product is production-ready.

Use the existing repository assessment, architecture, gap analysis, feature matrix, and file implementation plan as the source of truth. Revalidate them against the current code because previous edits may have changed dependencies.

# Autonomous Execution Loop

Repeat the following loop until the completion gate is satisfied.

## Step 1: Select the Next Incomplete Vertical Slice

Choose the highest-priority incomplete feature that can be completed end-to-end.

A vertical slice must include all applicable layers:

* domain types
* configuration
* API schema
* API route
* authentication
* authorization
* validation
* application service
* provider or infrastructure adapter
* persistence
* audit
* observability
* typed API client
* CLI command
* documentation
* tests

Do not implement disconnected layers that leave the user-visible feature unusable.

## Step 2: Trace Before Editing

For the selected feature:

1. Trace every caller.
2. Trace every imported type.
3. Trace route registration.
4. Trace dependency injection.
5. Trace persistence.
6. Trace provider interaction.
7. Trace current tests.
8. Identify backward-compatibility constraints.
9. Identify security and tenant-isolation requirements.
10. Identify failure, timeout, retry, and cancellation behavior.

## Step 3: Implement File by File

For each file:

1. Read the whole relevant file.
2. Read directly related files.
3. Make the smallest complete architectural change.
4. Preserve public interfaces unless migration is intentional.
5. Add explicit types.
6. Validate all external input.
7. Normalize errors.
8. Add structured logging with redaction.
9. Add metrics or tracing at meaningful boundaries.
10. Add or update tests immediately.
11. Update documentation when behavior changes.

Never create a second abstraction when the repository already has a suitable canonical abstraction.

Never copy provider-specific behavior into CLI code.

Never store provider credentials in client-side configuration.

## Step 4: Validate the Slice

Run:

* formatter
* lint
* type checker
* unit tests for modified modules
* API tests
* CLI tests
* integration tests for the feature
* security-focused tests
* schema drift check
* database migration check where applicable

Fix every newly introduced failure.

## Step 5: Adversarial Review

Before marking the slice complete, test mentally and programmatically:

* expired token
* invalid token
* wrong organization
* wrong workspace
* missing permission
* malformed request
* unsupported model
* unavailable provider
* rate limit
* network timeout
* stream disconnect
* user cancellation
* duplicate request
* duplicate job
* stale approval
* denied approval
* oversized file
* invalid MIME type
* malicious filename
* command injection attempt
* path traversal attempt
* secret in provider error
* partial database failure
* queue failure
* worker crash
* application restart

Add tests for relevant cases.

## Step 6: Update Implementation Records

Update:

* feature matrix
* file implementation plan
* change log
* final validation report

Do not mark a feature complete unless its production path and failure paths are tested.

# Required Architectural Invariants

Continuously verify:

1. CLI imports no provider SDK.
2. CLI has no provider credential configuration.
3. CLI uses one canonical typed API client.
4. API routes contain minimal orchestration logic.
5. Business logic is in application services.
6. Provider-specific code remains behind adapters.
7. Persistence remains behind repositories or clearly defined data-access boundaries.
8. Every tenant-owned record is scoped by organization and workspace.
9. Every mutating operation is authorized and audited.
10. Every stream reaches one terminal event.
11. Cancellation propagates through CLI, API, provider or job runner, and persistence.
12. Retried operations do not create unintended duplicates.
13. Errors are typed and correlation IDs are preserved.
14. Secrets are redacted.
15. OpenAPI and runtime contracts match.
16. The platform installation is standalone; nothing is installed outside the `z-platform` repository.

# API Client Requirements

Ensure the canonical client provides:

* authenticated requests
* refresh-once behavior
* timeout configuration
* retry policy for safe failures
* idempotency keys
* correlation IDs
* pagination
* multipart upload
* streaming
* cancellation
* typed errors
* API-version compatibility
* user-agent metadata
* debug logging with redaction

Do not retry:

* authentication failures
* authorization failures
* validation errors
* non-idempotent operations without an idempotency key
* explicit user cancellation

Use bounded exponential backoff with jitter for retryable failures.

# Streaming Requirements

The streaming implementation must:

* parse partial network frames
* handle multiple events in one frame
* handle UTF-8 split boundaries
* preserve event ordering
* report malformed events
* handle heartbeat events
* handle provider errors
* persist terminal state
* flush the final partial output
* support Ctrl+C cancellation
* close network resources
* avoid duplicate final messages
* expose usage data
* expose stop reason
* return a meaningful process exit code

Add deterministic streaming tests.

# Tool and Approval Requirements

A tool cannot execute unless:

* the tool exists
* its schema validates
* the user is authorized
* the workspace allows it
* required grants exist
* required approval is approved and unexpired
* execution policy permits it
* resource limits are defined

Every execution must record:

* actor
* organization
* workspace
* conversation or job
* tool
* normalized input hash
* approval identity
* start time
* end time
* result status
* resource usage
* redacted error
* correlation ID

# Final Repository-Wide Validation

When all slices appear complete, run the full repository validation:

1. Clean dependency installation.
2. Formatting check.
3. Lint.
4. Type checking.
5. Unit tests.
6. Integration tests.
7. End-to-end tests.
8. Security tests.
9. API schema drift check.
10. Database migration from an empty database.
11. Database upgrade from the previous supported version.
12. CLI package build.
13. Server package build.
14. Production bundle build.
15. Container build.
16. Container startup smoke test.
17. Health/readiness checks.
18. CLI-to-API smoke test.
19. Streaming smoke test.
20. File-upload smoke test.
21. Tool-approval smoke test.
22. Job cancellation smoke test.
23. Secret exposure scan.
24. Dependency vulnerability scan.

# Final Source Inspection

Search the final repository for:

* direct provider SDK imports in CLI or frontend
* provider API keys outside server configuration
* TODO
* FIXME
* HACK
* NotImplemented
* placeholder
* stub
* mock-only production code
* disabled tests
* broad lint suppressions
* broad type suppressions
* hard-coded localhost URLs
* hard-coded credentials
* unsafe shell execution
* unscoped database queries
* missing authorization
* secret logging

Resolve every material finding.

# Final Response Format

When and only when all possible work is complete, report:

## Completion Status

* overall status
* production readiness
* confidence level

## Implemented Features

Map every product feature to its implementation.

## Source Changes

Provide every created, modified, moved, and deleted file.

## CLI-to-API Flow

Describe the final runtime path.

## API Surface

List every endpoint and authentication requirement.

## Security

List implemented controls and residual risks.

## Testing Evidence

Provide exact commands, test counts, failures, and pass results.

## Deployment

Provide required environment variables, migration commands, startup commands, health checks, and rollback steps.

## Remaining Limitations

List only genuine unresolved external constraints.

Do not claim completion if validation is failing.
Do not hide failures.
Do not stop because one test is difficult.
Fix root causes rather than weakening checks.
Continue the loop until no further repository-local implementation work remains.
