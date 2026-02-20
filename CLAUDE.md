# HookDash

Phase: SCAFFOLDING

## Project Spec
- **Idea**: HookDash is a webhook inspection, debugging, and forwarding platform. Developers create unique webhook endpoints, point their third-party services (Stripe, GitHub, Twilio, Shopify, etc.) at those endpoints, and HookDash captures every incoming request with full headers, body, query params, and metadata. Users can inspect payloads in a clean UI, search/filter history, forward webhooks to local dev or staging servers, and retry failed deliveries. It eliminates the pain of debugging webhook integrations.
- **Target users**: Developers and engineering teams integrating with webhook-based APIs. Freelancers building payment/e-commerce integrations. DevOps teams monitoring webhook pipelines.
- **Revenue model**: Freemium SaaS
  - **Free**: 2 endpoints, 100 requests/day, 24-hour history
  - **Pro ($12/mo)**: 25 endpoints, 10K requests/day, 30-day history, forwarding, custom response codes
  - **Team ($39/mo)**: Unlimited endpoints, 100K requests/day, 90-day history, team workspaces, API access
- **Tech stack**: Python, FastAPI, SQLite (MVP with async aiosqlite), Jinja2 + Tailwind CSS (CDN), APScheduler for cleanup jobs, Docker
- **MVP scope**:
  1. User authentication (register, login, JWT httponly cookies)
  2. Create/manage webhook endpoints (unique URL per endpoint)
  3. Receive and store any incoming HTTP request to an endpoint
  4. Browse webhook history with search and filtering
  5. Inspect full request details (method, headers, body, query params, timestamp, source IP)
  6. Forward captured webhooks to a target URL with retry
  7. Dashboard with endpoint stats (request counts, success rates, recent activity)
  8. Professional responsive UI with real-time-feel updates

## Architecture Decisions
- **Webhook URLs**: Path-based routing — `POST/GET/PUT/etc /hooks/{endpoint_uuid}` catches all webhooks. UUIDs ensure uniqueness and unguessability.
- **Storage**: SQLite via async SQLAlchemy + aiosqlite. Webhook payloads stored as JSON text. Headers stored as JSON text. Adequate for MVP scale.
- **Auth**: JWT tokens in httponly cookies, bcrypt password hashing, same pattern as other SaaS Factory projects.
- **Forwarding**: Background task via FastAPI's BackgroundTasks for immediate forwarding. APScheduler for retry logic (exponential backoff, max 5 retries).
- **Cleanup**: APScheduler job runs daily to purge expired webhook data based on plan retention (24h free, 30d pro, 90d team).
- **Request size limit**: 1MB max body size per webhook to prevent abuse.
- **Rate limiting**: Simple in-memory rate limiter per endpoint (based on plan tier).
- **UI**: Server-side rendered with Jinja2 + Tailwind CSS via CDN + Inter font. HTMX for dynamic updates without full page reloads.
- **Migrations**: Alembic from the start.
- **Config**: Pydantic Settings for env var configuration.
- **Testing**: pytest + httpx async test client + in-memory SQLite.

## Task Backlog
- [ ] Create project structure, pyproject.toml, and FastAPI app skeleton with health check
- [ ] Set up database models (User, Endpoint, WebhookRequest, ForwardingConfig, ForwardingLog)
- [ ] Set up Alembic migrations and create initial migration
- [ ] Implement auth system (register, login, logout, JWT middleware, password hashing)
- [ ] Build auth UI (login page, register page, auth templates)
- [ ] Implement endpoint CRUD (create, list, edit, delete webhook endpoints)
- [ ] Build endpoint management UI (dashboard, create/edit forms)
- [ ] Implement webhook receiver (catch-all route that stores incoming requests)
- [ ] Build webhook history view and request detail inspection UI
- [ ] Implement webhook forwarding engine with retry logic (background tasks + APScheduler)
- [ ] Build forwarding configuration UI and forwarding logs view
- [ ] Build main dashboard with stats, charts, and recent activity
- [ ] Add search, filtering, and pagination across all list views
- [ ] Write comprehensive test suite (auth, endpoints, receiver, forwarding, API)
- [ ] Write Dockerfile and docker-compose.yml
- [ ] Write README with setup, usage, and deployment instructions

## Progress Log
### Session 1 — IDEATION
- Chose idea: HookDash — Webhook inspection, debugging, and forwarding platform
- Created spec and task backlog
- Rationale: Every developer integrating webhooks needs inspection/debugging tools. Existing solutions (Webhook.site, Hookdeck, RequestBin) validate strong market demand. The core functionality (receive HTTP, store, display, forward) maps well to a 10-15 session build.

## Known Issues
(none yet)

## Files Structure
```
hook-dash/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── alembic/
│   └── versions/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── endpoints.py
│       │   ├── receiver.py
│       │   ├── dashboard.py
│       │   └── forwarding.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── endpoint.py
│       │   ├── webhook_request.py
│       │   └── forwarding.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── endpoint.py
│       │   └── webhook.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── endpoint.py
│       │   ├── receiver.py
│       │   └── forwarding.py
│       └── templates/
│           ├── base.html
│           ├── login.html
│           ├── register.html
│           ├── dashboard.html
│           ├── endpoints/
│           │   ├── list.html
│           │   ├── detail.html
│           │   └── create.html
│           └── webhooks/
│               ├── history.html
│               └── detail.html
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_auth.py
    ├── test_endpoints.py
    ├── test_receiver.py
    └── test_forwarding.py
```
