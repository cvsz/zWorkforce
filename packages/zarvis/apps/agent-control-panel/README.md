# Z.A.R.V.I.S. Agent Control Panel

Operator-facing Next.js application for managing approved provider configuration
and rotation state through server-side platform boundaries. Provider credentials
must never be embedded in browser bundles or committed configuration.

## Getting Started

From `packages/zarvis`, install and validate the workspace:

```bash
pnpm install --frozen-lockfile
pnpm peers check
pnpm --filter agent-control-panel dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

Run production validation with:

```bash
pnpm --filter agent-control-panel build
pnpm --filter agent-control-panel lint
```

## Dependency policy

ESLint and TypeScript major updates are accepted only when the installed Next.js
and TypeScript ESLint plugin graph declares compatible peer ranges. Do not bypass
`pnpm peers check` with forced or legacy-peer options.
