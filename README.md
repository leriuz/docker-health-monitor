# 🩺 Docker Health Monitor

A containerized health-check system that monitors HTTP endpoints and displays results in a real-time dashboard. Built with Docker Compose, Python, Flask, and SQLite.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Health Checker  │────▶│   SQLite (vol)    │◀────│  Dashboard   │
│  (cron-style)   │     │  check_results.db │     │  (Flask UI)  │
└─────────────────┘     └──────────────────┘     └──────┬───────┘
        │                                               │
        ▼                                               ▼
  Checks endpoints                              http://localhost:8080
  every N seconds                               Shows status + history
```

## Quick Start

```bash
git clone https://github.com/leriuz/docker-health-monitor.git
cd docker-health-monitor
cp config.example.yaml config.yaml   # Edit your endpoints
docker compose up --build
```

Open **http://localhost:8080** to see the dashboard.

## Configuration

Edit `config.yaml` to define endpoints:

```yaml
check_interval: 30  # seconds between checks

endpoints:
  - name: "Production API"
    url: "https://api.example.com/health"
    method: GET
    timeout: 10
    expected_status: 200

  - name: "Auth Service"
    url: "https://auth.example.com/ping"
    method: GET
    timeout: 5
    expected_status: 200

  - name: "Webhook Endpoint"
    url: "https://hooks.example.com/status"
    method: POST
    timeout: 15
    expected_status: 200
    headers:
      Authorization: "Bearer ${AUTH_TOKEN}"
    body:
      action: "ping"

alerts:
  consecutive_failures: 3  # alert after N consecutive fails
  webhook_url: ""          # optional Slack/Discord webhook
```

Environment variables in headers/body are expanded at runtime via `${VAR_NAME}` syntax.

## Project Structure

```
docker-health-monitor/
├── docker-compose.yml
├── config.yaml
├── config.example.yaml
├── healthcheck/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── checker.py          # Main check loop
│   ├── config_loader.py    # YAML config parser
│   ├── db.py               # SQLite operations
│   └── notifier.py         # Alert notifications
├── dashboard/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py              # Flask application
│   ├── templates/
│   │   └── index.html      # Dashboard UI
│   └── static/
│       └── style.css
├── .gitignore
├── .env.example
└── README.md
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `checker` | — | Runs health checks on a loop, writes to SQLite |
| `dashboard` | 8080 | Serves status UI, reads from SQLite |

Both services share a Docker volume (`monitor-data`) for the SQLite database.

## Dashboard Features

- Live endpoint status (UP / DOWN / DEGRADED)
- Response time history (last 50 checks per endpoint)
- Uptime percentage (24h rolling window)
- Last check timestamp and response details
- Auto-refresh every 15 seconds

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHECK_INTERVAL` | `30` | Override config check interval |
| `DB_PATH` | `/data/checks.db` | SQLite database path |
| `DASHBOARD_PORT` | `8080` | Dashboard listen port |
| `AUTH_TOKEN` | — | Example token for authenticated endpoints |

## Development

Run without Docker for local development:

```bash
# Terminal 1: Health checker
cd healthcheck
pip install -r requirements.txt
python checker.py --config ../config.yaml

# Terminal 2: Dashboard
cd dashboard
pip install -r requirements.txt
python app.py
```

## License

MIT
