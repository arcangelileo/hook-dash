# HookDash

Webhook inspection, debugging, and forwarding platform.

HookDash captures every incoming webhook with full headers, body, query params, and metadata. Debug integrations in seconds, not hours.

## Features

- **Unique Webhook Endpoints** — Create endpoints with unique URLs for each integration
- **Full Request Inspection** — View method, headers, body, query params, source IP, timestamps
- **Auto-Forwarding** — Forward captured webhooks to localhost or staging with retry logic and exponential backoff
- **Replay Requests** — Manually replay any captured webhook to your forwarding target
- **Dashboard & Analytics** — Monitor request volume, success rates, and recent activity
- **Search & Filter** — Find any request in your history by method, content, or time range
- **Forwarding Logs** — Track every forwarding attempt with status codes, response times, and error details
- **Plan-Based Limits** — Free, Pro, and Team tiers with configurable endpoint and request limits

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the app
uvicorn app.main:app --reload --app-dir src

# Run tests
pytest
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), SQLite (aiosqlite)
- **Frontend**: Jinja2, Tailwind CSS (CDN), HTMX
- **Auth**: JWT (httponly cookies), bcrypt password hashing
- **HTTP Client**: httpx for webhook forwarding
- **Migrations**: Alembic with async SQLAlchemy support

## Development

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload --app-dir src --port 8000

# Run tests
pytest -v
```

### Environment Variables

All configuration is done via environment variables with the `HOOKDASH_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOOKDASH_SECRET_KEY` | `change-me-in-production...` | JWT signing secret (change in production!) |
| `HOOKDASH_DATABASE_URL` | `sqlite+aiosqlite:///./hookdash.db` | Database connection URL |
| `HOOKDASH_DEBUG` | `false` | Enable debug mode |
| `HOOKDASH_MAX_BODY_SIZE` | `1048576` | Max webhook body size in bytes (1MB) |

You can also create a `.env` file in the project root.

## Docker

```bash
# Build and run with Docker Compose
docker compose up -d

# Or build manually
docker build -t hookdash .
docker run -p 8000:8000 -e HOOKDASH_SECRET_KEY=your-secret-key hookdash
```

The app will be available at `http://localhost:8000`.

## Usage

1. **Register** an account at `/auth/register`
2. **Create an endpoint** from the dashboard — you'll get a unique webhook URL
3. **Point your service** (Stripe, GitHub, Shopify, etc.) at your HookDash URL
4. **Inspect requests** — every incoming webhook is captured with full details
5. **Set up forwarding** — configure a target URL to forward webhooks to your local dev server
6. **Replay requests** — click Replay on any captured webhook to re-forward it

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Landing page |
| `GET` | `/health` | Health check |
| `GET/POST` | `/auth/register` | User registration |
| `GET/POST` | `/auth/login` | User login |
| `GET/POST` | `/auth/logout` | User logout |
| `GET` | `/dashboard` | Dashboard with stats |
| `GET` | `/endpoints` | List user endpoints |
| `GET/POST` | `/endpoints/new` | Create endpoint |
| `GET` | `/endpoints/{id}` | Endpoint detail + webhook history |
| `GET/POST` | `/endpoints/{id}/edit` | Edit endpoint |
| `POST` | `/endpoints/{id}/delete` | Delete endpoint |
| `POST` | `/endpoints/{id}/forwarding` | Configure forwarding |
| `POST` | `/endpoints/{id}/forwarding/delete` | Remove forwarding |
| `GET` | `/endpoints/{id}/forwarding/logs` | View forwarding logs |
| `POST` | `/endpoints/{id}/replay/{req_id}` | Replay a webhook |
| `*` | `/hooks/{endpoint_id}` | Webhook receiver (all HTTP methods) |

## Project Structure

```
hook-dash/
├── src/app/
│   ├── main.py              # FastAPI app setup
│   ├── config.py            # Settings (env vars)
│   ├── database.py          # Async SQLAlchemy
│   ├── dependencies.py      # Auth dependencies
│   ├── api/                 # Route handlers
│   │   ├── auth.py          # Auth routes
│   │   ├── dashboard.py     # Dashboard
│   │   ├── endpoints.py     # Endpoint CRUD
│   │   ├── forwarding.py    # Forwarding config & logs
│   │   └── receiver.py      # Webhook receiver
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── templates/           # Jinja2 templates
├── tests/                   # Test suite (87 tests)
├── alembic/                 # Database migrations
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## License

MIT
