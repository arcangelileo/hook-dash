# HookDash

Phase: DEVELOPMENT

## Project Spec
- **Repo**: https://github.com/arcangelileo/hook-dash
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
- [x] Create project structure, pyproject.toml, and FastAPI app skeleton with health check
- [x] Set up database models (User, Endpoint, WebhookRequest, ForwardingConfig, ForwardingLog)
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

### Session 2 — SCAFFOLDING
- Created full project structure matching planned architecture
- Set up pyproject.toml with all dependencies (FastAPI, SQLAlchemy async, Alembic, JWT, bcrypt, HTMX, APScheduler, httpx, pytest)
- Built FastAPI app with `/health` endpoint and professional landing page
- Created all 5 database models with full SQLAlchemy mapped columns and relationships:
  - User (id, email, password_hash, name, plan, timestamps)
  - Endpoint (id, user_id, name, description, is_active, response config, request_count, timestamps)
  - WebhookRequest (id, endpoint_id, method, headers, body, query_params, content_type, source_ip, body_size, timestamp)
  - ForwardingConfig (id, endpoint_id, target_url, is_active, max_retries, timeout_seconds, timestamps)
  - ForwardingLog (id, forwarding_config_id, webhook_request_id, status_code, success, error_message, attempt_number, response_time_ms, timestamp)
- Created Pydantic schemas for auth, endpoints, and webhook requests
- Set up Alembic with async SQLAlchemy support
- Created base HTML template (Tailwind CSS CDN + Inter font + HTMX)
- Created professional landing page with hero, features grid, pricing section, and footer
- Set up test infrastructure: pytest-asyncio, in-memory SQLite, httpx AsyncClient
- All tests passing (2/2): health check + landing page
- Created GitHub repo: https://github.com/arcangelileo/hook-dash
- Pushed to both master and main branches

## Known Issues
(none yet)

## Files Structure
```
hook-dash/
├── CLAUDE.md
├── README.md
├── .gitignore
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── .gitkeep
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI app, lifespan, health check, landing page
│       ├── config.py            # Pydantic Settings (env vars, plan limits)
│       ├── database.py          # Async SQLAlchemy engine, session, Base
│       ├── api/
│       │   ├── __init__.py
│       │   ├── auth.py          # Auth router (stub)
│       │   ├── endpoints.py     # Endpoint CRUD router (stub)
│       │   ├── receiver.py      # Webhook receiver router (stub)
│       │   ├── dashboard.py     # Dashboard router (stub)
│       │   └── forwarding.py    # Forwarding router (stub)
│       ├── models/
│       │   ├── __init__.py      # Re-exports all models
│       │   ├── user.py          # User model
│       │   ├── endpoint.py      # Endpoint model
│       │   ├── webhook_request.py  # WebhookRequest model
│       │   └── forwarding.py    # ForwardingConfig + ForwardingLog models
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── auth.py          # RegisterRequest, LoginRequest, UserResponse
│       │   ├── endpoint.py      # EndpointCreate, EndpointUpdate, EndpointResponse
│       │   └── webhook.py       # WebhookRequestResponse
│       ├── services/
│       │   ├── __init__.py
│       │   ├── auth.py          # Auth service (stub)
│       │   ├── endpoint.py      # Endpoint service (stub)
│       │   ├── receiver.py      # Receiver service (stub)
│       │   └── forwarding.py    # Forwarding service (stub)
│       └── templates/
│           ├── base.html        # Base layout (Tailwind, Inter, HTMX)
│           └── landing.html     # Public landing page
└── tests/
    ├── __init__.py
    ├── conftest.py              # Async test fixtures, in-memory SQLite
    ├── test_health.py           # Health check + landing page tests
    ├── test_auth.py             # Auth tests (stub)
    ├── test_endpoints.py        # Endpoint tests (stub)
    ├── test_receiver.py         # Receiver tests (stub)
    └── test_forwarding.py       # Forwarding tests (stub)
```
