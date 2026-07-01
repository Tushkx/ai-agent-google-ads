# Make (Integromat) setup

Same flow as n8n: **schedule → Google Ads → HTTP POST → agent**.

## Scenario outline

1. **Schedule** — run every 1 / 6 / 12 / 24 hours (your choice)
2. **Google Ads** — search campaigns module, get keyword report (last 14 days)
3. **Iterator + Array aggregator** — build `rows` array
4. **HTTP — Make a request**
   - URL: `https://YOUR_DOMAIN/webhook/run`
   - Method: POST
   - Headers: `X-API-Key: YOUR_SECRET`
   - Body type: Raw / JSON

## JSON body template

```json
{
  "rows": {{map array to keyword rows}},
  "daily_budget": 20,
  "source": "google_ads_api",
  "send_notifications": true
}
```

Each row object:

```json
{
  "Keyword": "crm software free trial",
  "Date": "2026-06-01",
  "Clicks": 42,
  "Spend": 38.5,
  "Conversions": 4
}
```

## Field mapping (Google Ads → agent)

| Google Ads field | Agent field |
|------------------|-------------|
| `keyword` / `ad_group_criterion.keyword.text` | `Keyword` |
| `segments.date` | `Date` |
| `metrics.clicks` | `Clicks` |
| `metrics.cost_micros / 1e6` | `Spend` |
| `metrics.conversions` | `Conversions` |

## Response

The API returns:

```json
{
  "ok": true,
  "run_id": "a1b2c3d4",
  "actions": { "pause": 3, "scale_up": 2, "total_keywords": 10 },
  "top_recommendations": [...]
}
```

Use this in a follow-up **Slack** or **Email** module.

## Testing

Import `examples/webhook-payload.json` as a static body for the first test run.

See also [n8n.md](./n8n.md) for cron expressions and architecture.
