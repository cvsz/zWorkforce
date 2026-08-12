# August 2026 Dependency Maintenance

## Scope

This record covers the combined Dependabot maintenance set integrated after the
ZARVIS API rename and Windows cross-platform restore correction.

## Accepted updates

- ZARVIS API: Uvicorn 0.52.1 and Redis 8.1.0.
- ZC services: aiobotocore 3.9.0, OpenTelemetry OTLP exporter 1.44.0,
  mypy 2.3.0, Pydantic 2.13.4, and bsdiff4 1.2.6 dependency floors.
- ZAI Coder backend: Ruff 0.16.2 dependency floor.
- Agent Control Panel: eslint-config-next 16.3.0 and @types/node 26.2.0.
- GitHub Actions: pnpm/action-setup v6.

## Deferred incompatible majors

- ESLint 10 is deferred because eslint-plugin-import, eslint-plugin-jsx-a11y,
  and eslint-plugin-react declare peer support through ESLint 9.
- TypeScript 7 is deferred because the installed typescript-eslint 8.67 toolchain
  declares TypeScript support below 6.1.

Dependabot ignores these two major-version proposals until the peer ecosystem is
compatible. Minor and patch security updates remain enabled.

## Required verification

- Root CI and PostgreSQL integration.
- ZARVIS frozen-lockfile install, peer check, and workspace tests.
- ZARVIS API route tests and dependency audit.
- CodeQL and Dependency Review.
- Ubuntu restore for ZARVIS Windows projects.
- Windows build, tests, packaging, and launch smoke check.

Production release approval remains separate and requires immutable release
records, external staging evidence, and explicit operator sign-off.
