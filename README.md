# HookDash

Webhook inspection, debugging, and forwarding platform.

HookDash captures every incoming webhook with full headers, body, query params, and metadata. Debug integrations in seconds, not hours.

## Features

- **Unique Webhook Endpoints** — Create endpoints with unique URLs for each integration
- **Full Request Inspection** — View method, headers, body, query params, source IP, timestamps
- **Auto-Forwarding** — Forward captured webhooks to localhost or staging with retry logic
- **Dashboard & Analytics** — Monitor request volume, success rates, and recent activity
- **Search & Filter** — Find any request in your history by method, content, or time range

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

- **Backend**: Python, FastAPI, SQLAlchemy (async), SQLite
- **Frontend**: Jinja2, Tailwind CSS (CDN), HTMX
- **Auth**: JWT (httponly cookies), bcrypt
- **Task Scheduling**: APScheduler

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

## License

MIT
