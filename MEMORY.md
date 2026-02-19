# Crypto Alert Bot

**Status:** Complete, ready to launch

**What:** Real-time crypto monitoring — arbitrage alerts, whale tracking, price notifications

**Stack:** Python, Docker

**Deployment:** `/opt/Crypto-Alert-Bot/`

---

## Secrets Management

**Pattern:** `/opt/secrets/crypto-alert-bot.env`

On prod, the `.env` file should be moved to:
```
/opt/secrets/crypto-alert-bot.env
```

Then update the bot to load from that path:
```python
from dotenv import load_dotenv
load_dotenv("/opt/secrets/crypto-alert-bot.env")
```

Or in Docker Compose:
```yaml
env_file:
  - /opt/secrets/crypto-alert-bot.env
```

---

## Built Components

- Price monitor (5 exchanges: Binance, Coinbase, Kraken, Bybit, KuCoin)
- Whale tracker (blockchain large tx monitoring)
- Alert manager (Telegram + Discord)

**Files:**
- `src/saas_main.py` — entry point
- `src/alert_manager.py` — handles deduplication
- `src/price_monitor.py` — price monitoring
- `src/whale_tracker.py` — whale alerts
