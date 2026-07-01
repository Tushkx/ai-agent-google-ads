# Google Ads AI Agent

White-label autonomous Google Ads manager. **No manual CSV uploads** — data flows from **Google Ads API** via **n8n** or **Make** on a schedule you define (every 1h, 6h, 12h, or daily). The agent detects waste, scales winners, enforces a daily budget cap, and surfaces results in a dark-mode dashboard.

## How it works

```
n8n / Make (Schedule)
    → Google Ads API (keyword report)
    → POST /webhook/run
    → Agent analyzes + saves snapshot
    → Dashboard shows last run
    → (optional) Slack webhook notification
```

## Features

- **Webhook API** (FastAPI) — designed for n8n & Make automation
- **Configurable schedule** — set interval in n8n/Make *or* use built-in scheduler (`1h` / `6h` / `12h` / `24h`)
- **Autonomous logic** — waste detection, winner scaling, €20 budget cap (configurable)
- **Strategic recommendations** — plain-language explanations
- **Dashboard** — Streamlit UI showing the latest automated run
- **White-label** — company name, colors, and notifications via env vars

## Quick start

```bash
git clone https://github.com/YOUR_USER/google-ads-ai-agent.git
cd google-ads-ai-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit API_KEY, COMPANY_NAME, etc.
```

### Run API + dashboard

```bash
# Terminal 1 — API (n8n/Make calls this)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Dashboard
streamlit run app.py
```

### Test without n8n

```bash
curl -X POST http://localhost:8000/webhook/demo -H "X-API-Key: change-me-to-a-long-random-secret"
```

Then open http://localhost:8501 — the dashboard shows the result.

## Webhook API

### `POST /webhook/run`

Send Google Ads keyword rows from n8n/Make:

```json
{
  "rows": [
    {
      "Keyword": "crm software free trial",
      "Date": "2026-06-01",
      "Clicks": 42,
      "Spend": 38.50,
      "Conversions": 4
    }
  ],
  "daily_budget": 20,
  "source": "google_ads_api"
}
```

**Header:** `X-API-Key: <your API_KEY>`

See [`examples/webhook-payload.json`](examples/webhook-payload.json).

### Other endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /status` | Last run, schedule config, webhook URL |
| `POST /webhook/demo` | Run with built-in demo data |

## Schedule options

### Option A — n8n / Make (recommended)

Set the schedule in your automation tool:

| Interval | n8n cron |
|----------|----------|
| Every 1 hour | `0 * * * *` |
| Every 6 hours | `0 */6 * * *` |
| Every 12 hours | `0 */12 * * *` |
| Daily at noon | `0 12 * * *` |

Full setup: [`docs/n8n.md`](docs/n8n.md) · [`docs/make.md`](docs/make.md)

### Option B — Built-in scheduler

```bash
SCHEDULE_INTERVAL=6h
INGEST_URL=https://your-n8n.app/webhook/google-ads-rows
python scheduler.py
```

`INGEST_URL` should return `{ "rows": [...] }` from Google Ads.

Set `SCHEDULE_INTERVAL=disabled` to trigger only via webhook.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPANY_NAME` | Your Company | Branding |
| `API_KEY` | *(empty)* | Webhook auth — **set in production** |
| `PUBLIC_API_URL` | — | Public URL shown in dashboard |
| `SCHEDULE_INTERVAL` | `6h` | Built-in scheduler: `1h` `6h` `12h` `24h` `disabled` |
| `INGEST_URL` | — | n8n webhook returning Google Ads rows |
| `SLACK_WEBHOOK_URL` | — | Real Slack notifications |
| `DEFAULT_DAILY_BUDGET` | `20` | Budget cap (€) |

Full list: [`.env.example`](.env.example)

## Docker

```bash
docker compose up --build
```

- API: http://localhost:8000
- Dashboard: http://localhost:8501

## Project structure

```
google-ads-ai-agent/
├── api.py              # FastAPI webhook (n8n/Make target)
├── app.py              # Streamlit dashboard
├── scheduler.py        # Optional built-in interval runner
├── config.py           # Env-based white-label config
├── agent/
│   ├── analyzer.py     # Autonomous logic engine
│   ├── pipeline.py     # Run → persist → notify
│   ├── storage.py      # Last-run JSON persistence
│   └── ...
├── docs/
│   ├── n8n.md
│   └── make.md
├── examples/
│   └── webhook-payload.json
└── data/state/         # Runtime snapshots (gitignored)
```

## Agent rules

| Signal | Action |
|--------|--------|
| ≥ €5 spend, 0 conversions | **Pause** |
| ≥ 20 clicks, ≥ 4% CR | **Scale up** |
| High CPC, low CR | Reduce bid |
| Otherwise | Hold |

## Deploy to GitHub

1. Create a new repo on GitHub
2. Push this project:

```bash
cd google-ads-ai-agent
git init
git add .
git commit -m "Initial commit: Google Ads AI Agent"
git remote add origin https://github.com/YOUR_USER/google-ads-ai-agent.git
git push -u origin main
```

3. Deploy API to Railway / Render / Fly.io
4. Set env vars from `.env.example`
5. Point n8n/Make webhook to `https://your-api/webhook/run`

## License

MIT
