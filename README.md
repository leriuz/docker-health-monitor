# 🩺 Docker Health Monitor

This tool watches your HTTP endpoints around the clock and shows you their status in a clean, auto-refreshing dashboard — all running in Docker, no external dependencies.

Built with Docker Compose, Python, Flask, and SQLite. Nothing exotic.

## How it works

A background checker polls your endpoints every N seconds and writes the results to a shared SQLite database. The dashboard reads from that same database and shows you what's up, what's down, and how things looked over time.

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

## Getting started

```bash
git clone https://github.com/leriuz/docker-health-monitor.git
cd docker-health-monitor
cp config.example.yaml config.yaml   # add your endpoints here
docker compose up --build
```

Open **http://localhost:8080** — that's it.

## Configuration

Everything lives in `config.yaml`. Here's a realistic example:

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
  consecutive_failures: 3  # ping after this many failures in a row
  webhook_url: ""          # paste a Slack or Discord webhook URL here
```

You can use `${VAR_NAME}` anywhere in headers or body — values are pulled from environment variables at runtime.

## What the dashboard shows

- **UP / DOWN / DEGRADED** status for each endpoint
- Response time history (last 50 checks per endpoint)
- 24-hour uptime percentage
- Last check time and full response details
- Auto-refreshes every 15 seconds — no babysitting required

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHECK_INTERVAL` | `30` | Overrides the interval from config |
| `DB_PATH` | `/data/checks.db` | Where the SQLite file lives |
| `DASHBOARD_PORT` | `8080` | Port the dashboard listens on |
| `AUTH_TOKEN` | — | Example token for authenticated endpoints |

## Services at a glance

| Service | Port | What it does |
|---------|------|--------------|
| `checker` | — | Polls endpoints in a loop, writes to SQLite |
| `dashboard` | 8080 | Serves the status UI, reads from SQLite |

Both share a Docker volume (`monitor-data`) so the database is accessible to both.

## Project layout

```
docker-health-monitor/
├── docker-compose.yml
├── config.yaml
├── config.example.yaml
├── healthcheck/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── checker.py          # main check loop
│   ├── config_loader.py    # parses the YAML config
│   ├── db.py               # SQLite reads/writes
│   └── notifier.py         # sends alerts
├── dashboard/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py              # Flask app
│   ├── templates/
│   │   └── index.html
│   └── static/
│       └── style.css
├── .gitignore
├── .env.example
└── README.md
```

## Running without Docker

Useful during development:

```bash
# Terminal 1 — run the checker
cd healthcheck
pip install -r requirements.txt
python checker.py --config ../config.yaml

# Terminal 2 — run the dashboard
cd dashboard
pip install -r requirements.txt
python app.py
```

## License

MIT
