# zeto — AI Content Factory & Publishing Automation

## Language and Coding Standards

- **Communication**: Always talk in Thai when interacting with users.
- **Code & Technical Assets**: All code, comments, documentation, and technical definitions must be in English.

> Zeto is the ZeaZ content-factory and publishing automation platform. The current release provides a Facebook Page automation dashboard; the execution plan expands it into a full AI-assisted Content Factory.

## Current Features

- **Dashboard** — KPI overview, quick post, mini activity feed
- **Compose** — Rich text + photo posts with live Facebook preview, file upload
- **Post Queue** — Add, manage, and publish queued posts on demand
- **Scheduler** — Cron-based auto-posting (default + custom schedules)
- **Page Feed** — View and delete live Facebook posts
- **History** — Local audit log of all publish actions
- **Settings** — Configure schedule, template, and queue behavior
- **Analytics** — Dashboard analytics visualizations
- **AI Generator** — AI-assisted generation entry point

## Product Direction

The target architecture is an end-to-end Content Factory:

`IDEATE → GENERATE → WRITE → APPROVE → SCHEDULE → PUBLISH → MONITOR → LEARN`

Implementation scope, milestones, acceptance criteria, safety gates, model routing, observability, and release sequencing are defined in [`exec-planing.md`](./exec-planing.md).

## Quick Start

```bash
cp .env.example .env
# Fill in FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN in .env

npm install
npm run dev   # starts on http://localhost:5000
```

## Configuration

| Variable                | Required | Description                   |
| ----------------------- | -------- | ----------------------------- |
| `FACEBOOK_PAGE_ID`      | ✅       | Facebook Page numeric ID      |
| `FACEBOOK_ACCESS_TOKEN` | ✅       | Long-lived Page Access Token  |
| `FB_API_VERSION`        | Optional | Graph API version             |
| `PORT`                  | Optional | Server port (default: 5000)   |
| `NODE_ENV`              | Optional | `development` or `production` |

## API Endpoints

### Facebook

| Method | Path                          | Description                        |
| ------ | ----------------------------- | ---------------------------------- |
| POST   | `/api/facebook/post-message`  | Publish text post                  |
| POST   | `/api/facebook/post-photo`    | Publish photo (URL or file upload) |
| GET    | `/api/facebook/posts`         | Get recent posts                   |
| DELETE | `/api/facebook/posts/:postId` | Delete a post                      |
| GET    | `/api/facebook/insights`      | Page stats                         |
| GET    | `/api/facebook/config`        | Connection status                  |

### Queue

| Method | Path                     | Description              |
| ------ | ------------------------ | ------------------------ |
| GET    | `/api/queue`             | List all queue items     |
| POST   | `/api/queue`             | Add item to queue        |
| DELETE | `/api/queue`             | Clear entire queue       |
| DELETE | `/api/queue/:id`         | Remove specific item     |
| POST   | `/api/queue/:id/publish` | Immediately publish item |

### Scheduler

| Method | Path                     | Description           |
| ------ | ------------------------ | --------------------- |
| GET    | `/api/schedules`         | List custom schedules |
| POST   | `/api/schedules`         | Add custom schedule   |
| PATCH  | `/api/schedules/:id`     | Update schedule       |
| DELETE | `/api/schedules/:id`     | Delete schedule       |
| POST   | `/api/scheduler/trigger` | Manual trigger        |
| POST   | `/api/scheduler/restart` | Restart with new cron |

### Other

| Method | Path            | Description      |
| ------ | --------------- | ---------------- |
| GET    | `/api/history`  | Post history log |
| GET    | `/api/settings` | Get settings     |
| PATCH  | `/api/settings` | Update settings  |
| GET    | `/health`       | Health check     |

## Architecture

```text
apps/zeto/
├── src/
│   ├── server.js        # Express app, routes, multer
│   ├── fbController.js  # Facebook Graph API + Queue/Schedule/History handlers
│   ├── scheduler.js     # node-cron job manager
│   ├── database/        # PostgreSQL pool and forward migrations
│   ├── repositories/    # Transactional data-access layer
│   └── db.js            # PostgreSQL operational-store facade
├── public/
│   ├── index.html       # SPA shell
│   ├── css/style.css    # Responsive dashboard theme
│   └── js/app.js        # Router, data loading, page logic
├── compose.yaml         # Production app and PostgreSQL stack
├── .env.example
├── exec-planing.md
└── package.json
```

## Getting a Facebook Page Access Token

1. Go to the Meta Developer Portal.
2. Create an App and add the Pages product.
3. Generate a Page Access Token for the target page.
4. Exchange it for the appropriate long-lived token when required.
5. Store it in `FACEBOOK_ACCESS_TOKEN` in `.env` or the production secret store.

## Security

- Never commit `.env` or provider tokens.
- Use environment-specific credentials with least privilege.
- Keep provider secrets server-side only.
- Use scoped Page permissions required by enabled features.
- Add auditable approval gates before autonomous publishing.
- Production hardening requirements are tracked in `exec-planing.md`.
