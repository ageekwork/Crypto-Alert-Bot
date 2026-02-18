# Crypto Monitoring Stack

Prometheus + Grafana + Alertmanager for monitoring cryptocurrency prices and alerts.

## Quick Start

```bash
cd monitoring
docker compose up -d
```

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3001 | admin/admin |
| Alertmanager | http://localhost:9093 | - |

## What It Monitors

- **Bitcoin (BTC)**
- **Ethereum (ETH)**
- **Cardano (ADA)**
- **Solana (SOL)**
- **Polkadot (DOT)**

## Metrics Collected

- Current price in USD
- 24h price change percentage
- Market cap
- 24h trading volume
- All-time high/low

## Alerts Configured

| Alert | Condition | Severity |
|-------|-----------|----------|
| Price Drop | >10% down in 24h | Warning |
| Severe Drop | >20% down in 24h | Critical |
| Price Pump | >15% up in 24h | Info |
| Volume Spike | 3x above 7-day avg | Warning |
| Near ATH | Within 5% of ATH | Info |

## Setup Notifications

Edit `alertmanager.yml` and uncomment/configure your preferred notification channels:

- Telegram (recommended)
- Discord
- Slack
- Webhook
- Email

### Telegram Example

```yaml
receivers:
  - name: 'telegram'
    telegram_configs:
      - bot_token: '123456789:ABCdefGHIjklMNOpqrSTUvwxyz'
        chat_id: '-1001234567890'
        message: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

## Dashboards

Pre-configured dashboards in `grafana/dashboards/`:

- **Crypto Price Monitor**: Prices, 24h changes, market cap, volume

## Maintenance

```bash
# View logs
docker logs -f prometheus
docker logs -f crypto-exporter

# Update prices manually (exporter fetches every 60s)
curl http://localhost:8001/metrics

# Restart stack
docker compose restart

# Stop and remove
docker compose down -v
```

## Customization

### Add More Coins

Edit `exporter/exporter.py` and add coins to the `COINS` list:

```python
COINS = ['bitcoin', 'ethereum', 'cardano', 'solana', 'polkadot', 'ripple']
```

See [CoinGecko coin list](https://api.coingecko.com/api/v3/coins/list) for IDs.

### Custom Alerts

Add new rules to `prometheus/rules/crypto.yml`:

```yaml
- alert: MyCustomAlert
  expr: crypto_price_usd > 100000
  for: 5m
  labels:
    severity: info
  annotations:
    summary: "BTC over $100k!"
```

Then reload Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
```
