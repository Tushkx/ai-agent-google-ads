# n8n setup

Connect Google Ads API to the agent on a schedule you choose (every hour, 6 hours, 12 hours, or daily).

## Architecture

```
Schedule Trigger (cron)
    → Google Ads node (fetch keyword report)
    → Code / Set node (map to rows[])
    → HTTP Request POST → your-agent/webhook/run
    → (optional) Slack node with response summary
```

## 1. Deploy the agent API

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

Set `API_KEY` and `PUBLIC_API_URL` in your environment.

## 2. Create n8n workflow

### Node 1 — Schedule Trigger

| Interval | Cron expression |
|----------|-----------------|
| Every 1 hour | `0 * * * *` |
| Every 6 hours | `0 */6 * * *` |
| Every 12 hours | `0 */12 * * *` |
| Once per day (noon) | `0 12 * * *` |

### Node 2 — Google Ads

Use the **Google Ads** node (or HTTP Request to Google Ads API) to pull a **keyword performance report** for the last 14 days.

Required fields per row:

- `Keyword`
- `Date`
- `Clicks`
- `Spend`
- `Conversions`

### Node 3 — Code (map to agent schema)

```javascript
const items = $input.all();
const rows = items.map(item => ({
  Keyword: item.json.keyword || item.json.Keyword,
  Date: item.json.date || item.json.Date,
  Clicks: Number(item.json.clicks ?? item.json.Clicks ?? 0),
  Spend: Number(item.json.cost ?? item.json.Spend ?? 0),
  Conversions: Number(item.json.conversions ?? item.json.Conversions ?? 0),
}));

return [{ json: { rows, daily_budget: 20, source: "google_ads_api" } }];
```

### Node 4 — HTTP Request

| Setting | Value |
|---------|-------|
| Method | POST |
| URL | `https://YOUR_DOMAIN/webhook/run` |
| Authentication | Header Auth |
| Header name | `X-API-Key` |
| Header value | your `API_KEY` |
| Body | JSON from previous node |

### Node 5 — Slack (optional)

Post `{{ $json.top_recommendations }}` or the full response to your channel.

## 3. Test with demo endpoint

```bash
curl -X POST https://YOUR_DOMAIN/webhook/demo \
  -H "X-API-Key: YOUR_API_KEY"
```

## 4. Check status

```bash
curl https://YOUR_DOMAIN/status
```

Returns last run time, schedule config, and webhook URL.

## Built-in scheduler (alternative)

If you host the full stack yourself instead of using n8n cron:

1. Set `SCHEDULE_INTERVAL=6h` (or `1h`, `12h`, `24h`)
2. Set `INGEST_URL` to an n8n **Webhook** node that returns `{ "rows": [...] }`
3. Run `python scheduler.py` alongside the API

The scheduler calls `INGEST_URL` on each tick, then runs the agent.
