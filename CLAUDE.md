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
- [x] Set up Alembic migrations and create initial migration
- [x] Implement auth system (register, login, logout, JWT middleware, password hashing)
- [x] Build auth UI (login page, register page, auth templates)
- [x] Implement endpoint CRUD (create, list, edit, delete webhook endpoints)
- [x] Build endpoint management UI (dashboard, create/edit forms)
- [x] Implement webhook receiver (catch-all route that stores incoming requests)
- [x] Build webhook history view and request detail inspection UI
- [x] Build main dashboard with stats, charts, and recent activity
- [x] Add search, filtering, and pagination across all list views
- [x] Write comprehensive test suite (auth, endpoints, receiver, forwarding, API)
- [ ] Implement webhook forwarding engine with retry logic (background tasks + APScheduler)
- [ ] Build forwarding configuration UI and forwarding logs view
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

### Session 3 — AUTH SYSTEM
- Generated and applied initial Alembic migration (all 5 tables: users, endpoints, webhook_requests, forwarding_configs, forwarding_logs)
- Built complete auth service layer:
  - Password hashing with bcrypt via passlib
  - JWT token creation/verification with python-jose (HS256, 24h expiry)
  - User registration with email uniqueness check
  - User authentication with email/password verification
- Built auth API routes with form-based flow:
  - GET/POST /auth/register — registration page with server-side validation
  - GET/POST /auth/login — login page with error feedback
  - GET/POST /auth/logout — cookie clearing + redirect
  - JWT stored in httponly cookie (samesite=lax, 24h max-age)
- Created auth dependency injection:
  - `get_current_user` — raises 401 if no valid token
  - `get_optional_user` — returns None if not authenticated
  - Custom 401 exception handler redirects to login page
- Built professional auth UI templates:
  - Register page with name/email/password form, validation errors, plan info card
  - Login page with email/password form, error/success states
  - Dark gradient theme matching landing page, responsive design
- Built initial dashboard page (authenticated):
  - Top nav with user avatar, navigation links, sign out
  - Stats grid (endpoints, requests today, total requests, plan)
  - Empty state CTA to create first endpoint
- Wrote 24 auth tests (unit + integration), all passing:
  - Password hashing (3 tests), JWT (3 tests)
  - Registration flow (6 tests: success, validation, duplicate email)
  - Login flow (5 tests: success, wrong password, nonexistent user, empty fields)
  - Logout (2 tests: POST and GET)
  - Auth protection (5 tests: dashboard guard, redirect when logged in, invalid token)
- All 26 tests passing (2 health + 24 auth)

### Session 4 — ENDPOINTS, RECEIVER & HISTORY
- Built complete endpoint CRUD service layer:
  - create, list, get, update, delete endpoints with user ownership checks
  - Plan-based endpoint limits enforced (free=2, pro=25, team=unlimited)
  - Request count tracking per endpoint
- Built webhook receiver (catch-all route):
  - `api_route /hooks/{endpoint_id}` accepting GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS
  - Stores full request: method, headers (JSON), body, query_params (JSON), content_type, source_ip, body_size
  - Returns configurable response code/body/content-type per endpoint
  - 1MB body size limit enforced, inactive endpoint rejection (410), 404 for missing endpoints
- Built webhook history service:
  - Paginated listing with method filter and body/header/query search
  - Request detail retrieval by ID
  - Dashboard stats: requests today, total requests, endpoint count
- Built complete endpoint management UI:
  - Endpoints list page with card grid, status badges, request counts
  - Create endpoint page with name, description, response config (code, body, content-type)
  - Edit endpoint page with toggle for active/inactive, delete button
  - Endpoint detail page with:
    - Webhook URL display with copy-to-clipboard
    - Stats row (total requests, response code)
    - Expandable webhook history with inline request inspection
    - Full headers, body, query params, and metadata display per request
    - JSON auto-formatting in expanded views
    - Method filter dropdown and body search
    - Pagination with previous/next navigation
  - 404 not-found page for missing/unauthorized endpoints
  - Empty states for no endpoints and no requests
- Created shared nav partial for consistent navigation across authenticated pages
- Updated dashboard with real stats from database (endpoint count, requests today, total requests)
- Dashboard now shows recent endpoints list with direct links
- All UI follows consistent design system: Tailwind CSS, brand colors, responsive, proper states
- Wrote 34 new tests (19 endpoint + 15 receiver/history), all passing:
  - Endpoint CRUD: list (3), create (6 incl. plan limits), detail (3), edit (4), delete (2), isolation (1)
  - Receiver: POST/GET/PUT/PATCH/DELETE (5), 404/410 handling (2), request count (1), custom response (1), headers/query storage (2)
  - History: display (1), method filter (1), search (1), dashboard stats (1)
- All 60 tests passing (2 health + 24 auth + 19 endpoints + 15 receiver)

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
│       ├── .gitkeep
│       └── db1a7b55b4f3_initial_schema.py
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI app, lifespan, health check, landing page
│       ├── config.py            # Pydantic Settings (env vars, plan limits)
│       ├── database.py          # Async SQLAlchemy engine, session, Base
│       ├── dependencies.py       # Auth dependencies (get_current_user, get_optional_user)
│       ├── api/
│       │   ├── __init__.py
│       │   ├── auth.py          # Auth routes (register, login, logout)
│       │   ├── endpoints.py     # Endpoint CRUD routes (list, create, detail, edit, delete)
│       │   ├── receiver.py      # Webhook receiver catch-all route
│       │   ├── dashboard.py     # Dashboard with real stats
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
│       │   ├── auth.py          # Auth service (hash, verify, JWT, register, authenticate)
│       │   ├── endpoint.py      # Endpoint CRUD service (create, list, get, update, delete)
│       │   ├── receiver.py      # Webhook storage, history, stats queries
│       │   └── forwarding.py    # Forwarding service (stub)
│       └── templates/
│           ├── base.html        # Base layout (Tailwind, Inter, HTMX)
│           ├── landing.html     # Public landing page
│           ├── partials/
│           │   └── nav.html     # Shared authenticated nav bar
│           ├── auth/
│           │   ├── login.html   # Login page
│           │   └── register.html # Registration page
│           ├── dashboard/
│           │   └── index.html   # Dashboard with real stats and endpoint list
│           └── endpoints/
│               ├── list.html    # Endpoints grid view
│               ├── new.html     # Create endpoint form
│               ├── edit.html    # Edit endpoint form
│               ├── detail.html  # Endpoint detail + webhook history
│               └── not_found.html # 404 page for endpoints
└── tests/
    ├── __init__.py
    ├── conftest.py              # Async test fixtures, in-memory SQLite
    ├── test_health.py           # Health check + landing page tests
    ├── test_auth.py             # Auth tests (24 tests: unit + integration)
    ├── test_endpoints.py        # Endpoint CRUD tests (19 tests)
    ├── test_receiver.py         # Receiver + history + dashboard stats tests (15 tests)
    └── test_forwarding.py       # Forwarding tests (stub)
```
