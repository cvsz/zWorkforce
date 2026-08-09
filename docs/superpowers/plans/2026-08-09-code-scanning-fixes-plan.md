# Code Scanning Security Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve every open CodeQL alert on `main` while preserving tenant isolation, SQLite/PostgreSQL behavior, and one-time secret handling. Existing unsalted API-key records require rotation.

**Architecture:** Keep the existing `api_keys2.key_hash` text column but store API-key verifiers as self-describing salted PBKDF2-HMAC-SHA256 records. Authentication will inspect bounded active repository rows and verify with constant-time comparison; legacy unsalted SHA-256 rows require key recreation/rotation and are not accepted. All response-header values will pass through explicit CR/LF sanitization and fixed static MIME mappings. The CLI will persist generated secrets in a mode-0600 file and print only non-sensitive metadata.

**Tech Stack:** Python 3.12–3.14, stdlib `http.server`, SQLite/PostgreSQL repository methods, `unittest`, GitHub CodeQL.

## Global Constraints

- Run `python -m compileall -q zworkforce tests` (using the available `python3` executable when `python` is absent).
- Run `PYTHONPATH=. python -m unittest discover -s tests -v`.
- Run `zworkforce doctor` (using `PYTHONPATH=. python3 -m zworkforce doctor` when the console script is absent).
- Run `tests/test_v3_postgres.py` against a real PostgreSQL service; do not treat skipped local tests as PostgreSQL verification.
- Do not introduce `shell=True` or provider/storage/database credentials into static assets.
- Route durable state changes through repository methods and preserve SQLite compatibility.
- Keep mutating behavior deny-by-default and bounded.
- Do not store API-key plaintext or print provider/API secrets to logs.

## Files and Responsibilities

- Modify `zworkforce/security.py`: PBKDF2 verifier creation, explicit legacy-verifier rejection, and constant-time authentication.
- Modify `zworkforce/db_governance.py`: repository method for bounded active-key lookup; make bootstrap upserts stable by key identity rather than a randomized verifier.
- Modify `zworkforce/api.py`: sanitize request IDs and CORS origins before response headers and use fixed MIME values for static assets.
- Modify `zworkforce/cli.py`: add secure one-time secret-file output for `key-create` and remove clear-text secret logging.
- Modify `tests/test_security_v2.py`: cover PBKDF2 storage, dynamic-key authentication, bootstrap rotation, legacy-verifier rejection, and constant-time failure behavior.
- Modify `tests/test_api_v2.py`: cover safe request-ID/CORS response behavior and fixed static response headers.
- Create `tests/test_cli_security.py`: verify `key-create` never places the secret in stdout and creates a mode-0600 secret file.
- Modify `docs/SECRET-MANAGEMENT.md` and the relevant README CLI section: document the secret-file output and rotation behavior.

### Task 1: Lock down response-header construction

**Files:**
- Modify: `zworkforce/api.py:64-80,144-152,159-170`
- Test: `tests/test_api_v2.py`

**Interfaces:**
- Add a small internal sanitizer that removes `\r` and `\n` from values before any `send_header` call.
- Keep request-ID format validation and CORS allowlisting; sanitize before validation and before echoing.
- Replace `mimetypes.guess_type` output for the three known static files with fixed constants.

- [ ] **Step 1: Write failing regression tests**

  Add tests that exercise a CR/LF-bearing request ID and Origin through a raw socket or the handler-level sanitizer, then assert no injected header appears. Add a static asset response assertion that the content type is one of the fixed constants.

- [ ] **Step 2: Run the focused tests and confirm RED**

  Run `PYTHONPATH=. python3 -m unittest tests.test_api_v2 -v`; the new assertions must fail against the current implementation for the expected header-construction reason.

- [ ] **Step 3: Implement the minimal fix**

  Add `_sanitize_header_value(value: str) -> str` in `api.py`, call it before request-ID validation and CORS allowlist checks, call it at every response-header sink, and emit fixed `text/html`, `text/javascript`, and `text/css` MIME values for known assets.

- [ ] **Step 4: Run the focused tests and confirm GREEN**

  Run `PYTHONPATH=. python3 -m unittest tests.test_api_v2 -v` and confirm all API tests pass.

### Task 2: Replace weak API-key hashing without breaking existing data

**Files:**
- Modify: `zworkforce/security.py:31-65,97-106,133-134`
- Modify: `zworkforce/db_governance.py:42-72`
- Test: `tests/test_security_v2.py`

**Interfaces:**
- Store new verifiers in the form `pbkdf2_sha256$<iterations>$<salt>$<digest>` using a per-key random salt and a documented constant work factor.
- Add repository method `list_active_api_keys(limit: int = 10000)`; both SQLite and PostgreSQL implementations use the existing shared SQL interface and enforce the active-row limit.
- Use a stable bootstrap key ID derived from tenant/name so repeated startup does not create duplicate active rows.
- Reject legacy 64-character SHA-256 rows so operators must recreate and rotate those credentials instead of retaining a weak verifier path.

- [ ] **Step 1: Write failing tests**

  Add tests asserting new records start with `pbkdf2_sha256$`, authentication succeeds for generated and bootstrap keys, wrong keys fail, legacy SHA-256 rows require rotation, and bootstrap rotation leaves exactly one active row for the name.

- [ ] **Step 2: Run the focused tests and confirm RED**

  Run `PYTHONPATH=. python3 -m unittest tests.test_security_v2 -v`; the new format and migration assertions must fail before implementation.

- [ ] **Step 3: Implement repository and verifier changes**

  Change bootstrap upsert conflict handling to use stable IDs, return at most 10,000 active candidates through repository methods, verify PBKDF2 with `hmac.compare_digest`, and reject legacy verifiers. Keep all writes inside repository methods and avoid exposing hashes in API responses.

- [ ] **Step 4: Run focused security tests and confirm GREEN**

  Run `PYTHONPATH=. python3 -m unittest tests.test_security_v2 -v`; confirm legacy rows are rejected and new-key paths pass on SQLite.

### Task 3: Remove CLI clear-text secret logging

**Files:**
- Modify: `zworkforce/cli.py:90-100,255-259`
- Create: `tests/test_cli_security.py`
- Modify: `docs/SECRET-MANAGEMENT.md` and the README CLI documentation

**Interfaces:**
- Add an optional `--secret-file PATH` argument to `key-create`; when omitted, create a file below the configured data directory with a restrictive mode and a non-sensitive generated filename.
- Write only the one-time API secret to that file with mode `0600`; stdout contains key metadata and the file path, never the secret.
- Refuse unsafe existing secret-file permissions rather than weakening them.

- [ ] **Step 1: Write failing tests**

  Invoke `cli.main(["key-create", ...])` with a temporary data directory and assert stdout does not contain the returned secret, the reported file exists with mode `0600`, and the file contains the secret.

- [ ] **Step 2: Run the focused test and confirm RED**

  Run `PYTHONPATH=. python3 -m unittest tests.test_cli_security -v`; it must fail because the current CLI prints the secret and has no file output.

- [ ] **Step 3: Implement secure file output**

  Use exclusive file creation and explicit permissions, return only non-sensitive JSON metadata, and preserve the API endpoint’s existing one-time response contract.

- [ ] **Step 4: Run the focused test and confirm GREEN**

  Run `PYTHONPATH=. python3 -m unittest tests.test_cli_security -v` and confirm the secret is absent from stdout.

### Task 4: Full verification and CodeQL closure

**Files:**
- Modify only the files required by Tasks 1–3 and documentation updates.

- [ ] **Step 1: Run the complete local gates**

  Run:

  ```bash
  python3 -m compileall -q zworkforce tests
  PYTHONPATH=. python3 -m unittest discover -s tests -v
  PYTHONPATH=. python3 -m zworkforce doctor
  python3 scripts/verify_release.py
  ```

- [ ] **Step 2: Run security invariants and PostgreSQL integration**

  Run the repository’s no-`shell=True`/no-static-secret checks and run `tests/test_v3_postgres.py` with `ZWORKFORCE_TEST_POSTGRES_URL` against a real PostgreSQL service.

- [ ] **Step 3: Inspect the diff and verify alert coverage**

  Confirm no unrelated files or secrets changed, then push the branch so CodeQL analyzes the new commit. Query the GitHub code-scanning API and require zero open alerts for the new commit before integration.

- [ ] **Step 4: Commit and integrate with a signed commit**

  Create a GPG-signed commit using the configured agent key, integrate the verified branch into `main`, push with an explicit lease, and verify the remote SHA, signature, clean worktree, CI, CodeQL, and release invariants.
