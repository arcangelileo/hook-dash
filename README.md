# HookDash

**Webhook inspection, debugging, and forwarding platform.**

HookDash gives developers instant visibility into every webhook hitting their integrations. Create unique endpoints, point Stripe / GitHub / Shopify / Twilio at them, and inspect the full request — headers, body, query params, source IP — in a clean, searchable UI. When you're ready to develop, forward captured webhooks to your local machine with automatic retries and replay any request on demand.

---

## Features

| Category | What you get |
|---|---|
| **Endpoint Management** | Create unlimited\* unique webhook URLs, toggle active/inactive, customize response codes & bodies |
| **Full Request Capture** | Every HTTP method, headers (JSON), body, query params, content type, source IP, body size, timestamp |
| **Request Inspection** | Expand any request inline — auto-formatted JSON, raw body, full header list, metadata |
| **Search & Filter** | Filter by HTTP method, full-text search across body/headers/query params, paginated history |
| **Auto-Forwarding** | Forward incoming webhooks to localhost or staging in real time with configurable retries (1-10) and exponential backoff |
| **Replay** | One-click replay of any captured webhook to your forwarding target |
| **Forwarding Logs** | Detailed log of every forwarding attempt — status code, response time, error messages, attempt number |
| **Dashboard** | At-a-glance stats: endpoint count, requests today, total requests, recent endpoints with quick links |
| **Plan-Based Limits** | Free, Pro ($12/mo), and Team ($39/mo) tiers with configurable endpoint, request, and retention limits |
| **Auth** | Secure registration & login with bcrypt password hashing and JWT httponly cookies |

\* Subject to plan limits (Free: 2, Pro: 25, Team: unlimited).

---

## Quick Start

### Docker (recommended)

```bash
# One-liner — build and run
docker compose up -d

# Open http://localhost:8000
```

Or without Compose:

```bash
docker build -t hookdash .
docker run -d -p 8000:8000 \
  -e HOOKDASH_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))") \
  -v hookdash-data:/app/data \
  hookdash
```

### Local Development

```bash
# Clone the repo
git clone https://github.com/arcangelileo/hook-dash.git
cd hook-dash

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the dev server (auto-reload enabled)
uvicorn app.main:app --reload --app-dir src --port 8000
```

Open **http://localhost:8000** — register an account and start creating endpoints.

---

## Usage Guide

1. **Register** — Create an account at `/auth/register`
2. **Create an endpoint** — From the dashboard, click "New Endpoint". Give it a name, optionally set a custom response code/body.
3. **Copy the webhook URL** — Each endpoint gets a unique URL like `https://your-host/hooks/a1b2c3d4-...`
4. **Point your service** at the HookDash URL (Stripe webhook settings, GitHub webhook config, etc.)
5. **Inspect requests** — Every incoming webhook appears in the endpoint detail view with full headers, body, and metadata.
6. **Set up forwarding** — On the endpoint detail page, configure a target URL (e.g. `http://localhost:3000/webhooks`), max retries, and timeout.
7. **Replay** — Click the Replay button on any captured webhook to re-forward it to your target.
8. **View forwarding logs** — See every forwarding attempt with status codes, response times, and error messages.

---

## API Reference

### Public

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Landing page |
| `GET` | `/health` | Health check — returns `{"status": "healthy"}` |

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `GET/POST` | `/auth/register` | User registration |
| `GET/POST` | `/auth/login` | User login |
| `GET/POST` | `/auth/logout` | User logout (clears JWT cookie) |

### Dashboard & Endpoints (requires auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/dashboard` | Dashboard with stats and recent endpoints |
| `GET` | `/endpoints` | List all user endpoints |
| `GET/POST` | `/endpoints/new` | Create a new endpoint |
| `GET` | `/endpoints/{id}` | Endpoint detail + webhook history |
| `GET/POST` | `/endpoints/{id}/edit` | Edit endpoint settings |
| `POST` | `/endpoints/{id}/delete` | Delete endpoint and all data |

### Forwarding (requires auth)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/endpoints/{id}/forwarding` | Create or update forwarding config |
| `POST` | `/endpoints/{id}/forwarding/delete` | Remove forwarding config |
| `GET` | `/endpoints/{id}/forwarding/logs` | Paginated forwarding logs |
| `POST` | `/endpoints/{id}/replay/{req_id}` | Replay a captured webhook |

### Webhook Receiver (public)

| Method | Path | Description |
|--------|------|-------------|
| `*` | `/hooks/{endpoint_id}` | Catches all HTTP methods (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS) |

---

## Configuration

All settings use the `HOOKDASH_` prefix and can be set via environment variables or a `.env` file. Copy `.env.example` to `.env` to get started.

| Variable | Default | Description |
|---|---|---|
| `HOOKDASH_SECRET_KEY` | `change-me-in-production...` | **Required in production.** JWT signing secret. Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `HOOKDASH_DATABASE_URL` | `sqlite+aiosqlite:///./hookdash.db` | Async database connection URL |
| `HOOKDASH_DEBUG` | `false` | Enable debug mode (verbose SQL logging) |
| `HOOKDASH_MAX_BODY_SIZE` | `1048576` | Max webhook body size in bytes (1 MB) |
| `HOOKDASH_ALGORITHM` | `HS256` | JWT algorithm |
| `HOOKDASH_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT token lifetime (24 hours) |
| `HOOKDASH_FREE_MAX_ENDPOINTS` | `2` | Free plan endpoint limit |
| `HOOKDASH_FREE_MAX_REQUESTS_PER_DAY` | `100` | Free plan daily request limit |
| `HOOKDASH_FREE_RETENTION_HOURS` | `24` | Free plan data retention |
| `HOOKDASH_PRO_MAX_ENDPOINTS` | `25` | Pro plan endpoint limit |
| `HOOKDASH_PRO_MAX_REQUESTS_PER_DAY` | `10000` | Pro plan daily request limit |
| `HOOKDASH_PRO_RETENTION_DAYS` | `30` | Pro plan data retention |
| `HOOKDASH_TEAM_MAX_ENDPOINTS` | `999999` | Team plan endpoint limit |
| `HOOKDASH_TEAM_MAX_REQUESTS_PER_DAY` | `100000` | Team plan daily request limit |
| `HOOKDASH_TEAM_RETENTION_DAYS` | `90` | Team plan data retention |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Browser / Third-Party Service                           │
│  (Stripe, GitHub, Shopify, Twilio, ...)                  │
└──────────────┬───────────────────────────────────────────┘
               │ HTTP request
               ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI Application                                     │
│                                                          │
│  ┌─────────┐ ┌───────────┐ ┌──────────┐ ┌────────────┐  │
│  │  Auth   │ │ Dashboard │ │Endpoints │ │  Receiver  │  │
│  │ Routes  │ │  Routes   │ │  CRUD    │ │  (catch-   │  │
│  │         │ │           │ │  Routes  │ │   all)     │  │
│  └────┬────┘ └─────┬─────┘ └────┬─────┘ └─────┬──────┘  │
│       │             │            │              │         │
│  ┌────▼─────────────▼────────────▼──────────────▼──────┐  │
│  │               Service Layer                         │  │
│  │  auth.py · endpoint.py · receiver.py · forwarding.py│  │
│  └─────────────────────┬───────────────────────────────┘  │
│                        │                                 │
│  ┌─────────────────────▼───────────────────────────────┐  │
│  │           SQLAlchemy Async + aiosqlite              │  │
│  │  User · Endpoint · WebhookRequest · ForwardingConfig│  │
│  └─────────────────────┬───────────────────────────────┘  │
│                        │                                 │
│  ┌─────────────────────▼───────────┐  ┌────────────────┐  │
│  │        SQLite Database          │  │  Background    │  │
│  │   (data/hookdash.db)           │  │  Forwarding    │  │
│  └─────────────────────────────────┘  │  (httpx +      │  │
│                                       │   retries)     │  │
│                                       └───────┬────────┘  │
│                                               │          │
└───────────────────────────────────────────────┼──────────┘
                                                │ HTTP
                                                ▼
                                  ┌──────────────────────┐
                                  │  Developer's Local   │
                                  │  Server / Staging    │
                                  └──────────────────────┘
```

### Tech Stack

| Layer | Technology |
|---|---|
| **Runtime** | Python 3.11+, FastAPI, Uvicorn |
| **Database** | SQLite via async SQLAlchemy + aiosqlite |
| **Migrations** | Alembic (async) |
| **Auth** | JWT (httponly cookies), bcrypt (passlib) |
| **Frontend** | Jinja2 templates, Tailwind CSS (CDN), HTMX |
| **HTTP Client** | httpx (async, for webhook forwarding) |
| **Config** | Pydantic Settings (environment variables) |
| **Container** | Docker multi-stage build, non-root user |

### Key Design Decisions

- **Path-based webhook URLs**: `/hooks/{uuid}` — UUIDs are unguessable and unique.
- **SQLite for MVP**: Zero operational overhead. Data stored in a single volume-mounted file. Swap to PostgreSQL by changing `DATABASE_URL`.
- **JWT in httponly cookies**: Secure by default — no tokens in localStorage, no XSS risk.
- **Background forwarding**: FastAPI `BackgroundTasks` for immediate forwarding, exponential backoff for retries.
- **1 MB body limit**: Prevents abuse and memory exhaustion from oversized payloads.

---

## Project Structure

```
hook-dash/
├── src/app/
│   ├── main.py              # FastAPI app, lifespan, exception handlers
│   ├── config.py            # Pydantic Settings (env vars, plan limits)
│   ├── database.py          # Async SQLAlchemy engine + session factory
│   ├── dependencies.py      # Auth dependencies (get_current_user)
│   ├── api/
│   │   ├── auth.py          # Register, login, logout routes
│   │   ├── dashboard.py     # Dashboard with real-time stats
│   │   ├── endpoints.py     # Endpoint CRUD + detail views
│   │   ├── forwarding.py    # Forwarding config, logs, replay
│   │   └── receiver.py      # Webhook catch-all receiver
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py          # User (email, password, plan)
│   │   ├── endpoint.py      # Endpoint (name, response config)
│   │   ├── webhook_request.py  # Captured webhook data
│   │   └── forwarding.py    # ForwardingConfig + ForwardingLog
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic layer
│   │   ├── auth.py          # Password hashing, JWT, registration
│   │   ├── endpoint.py      # Endpoint CRUD with plan enforcement
│   │   ├── receiver.py      # Webhook storage, history, stats
│   │   └── forwarding.py    # Forwarding engine, retries, logs
│   └── templates/           # Jinja2 HTML templates
│       ├── base.html        # Base layout (Tailwind, HTMX, favicon)
│       ├── landing.html     # Public landing page with pricing
│       ├── error.html       # Branded error pages
│       ├── auth/            # Login & register pages
│       ├── dashboard/       # Dashboard view
│       ├── endpoints/       # Endpoint CRUD + detail views
│       └── forwarding/      # Forwarding logs view
├── tests/                   # 99 tests (pytest + httpx async)
│   ├── conftest.py          # Fixtures (in-memory SQLite, auth helpers)
│   ├── test_health.py       # Health check + landing (2)
│   ├── test_auth.py         # Auth flows (24)
│   ├── test_endpoints.py    # Endpoint CRUD (19)
│   ├── test_receiver.py     # Webhook receiver + history (15)
│   ├── test_forwarding.py   # Forwarding engine + UI (27)
│   └── test_qa.py           # QA regression tests (12)
├── alembic/                 # Database migrations
├── Dockerfile               # Multi-stage, non-root, health check
├── docker-compose.yml       # One-command deployment
├── .env.example             # Documented env var template
├── pyproject.toml           # Dependencies & build config
└── CLAUDE.md                # Development log & architecture
```

---

## Testing

```bash
# Run all 99 tests
pytest -v

# Run a specific test file
pytest tests/test_forwarding.py -v

# Run with coverage (install pytest-cov first)
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

Tests use an in-memory SQLite database and httpx `AsyncClient` — no external services required.

---

## Deployment Checklist

1. **Set `HOOKDASH_SECRET_KEY`** to a strong random value (see `.env.example`).
2. **Mount a persistent volume** for `/app/data` so the SQLite database survives container restarts.
3. **Put a reverse proxy** (Nginx, Caddy, Cloudflare Tunnel) in front for HTTPS.
4. **Set `HOOKDASH_DEBUG=false`** (the default) in production.
5. **Monitor** the `/health` endpoint with your uptime checker.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Make your changes and add tests
5. Run the test suite: `pytest -v`
6. Run the linter: `ruff check src/ tests/`
7. Commit and push: `git push origin feature/amazing-feature`
8. Open a Pull Request

---

## License

MIT
