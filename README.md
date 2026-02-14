# Crypto Alert Bot

**Real-time cryptocurrency monitoring with arbitrage detection, whale alerts, and price notifications.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 🎯 What It Does

Crypto Alert Bot monitors cryptocurrency markets 24/7 and sends you instant alerts when:

- **💰 Arbitrage opportunities** appear between exchanges (buy low, sell high)
- **📈 Price movements** exceed your thresholds (3%, 5%, 10%, etc.)
- **🐋 Whale transactions** move millions in crypto (potential volatility ahead)
- **⚡ Market divergences** between Polymarket predictions and real prices

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the skill
cd crypto_alert_bot

# Install dependencies
pip install requests

# Create config file
python skill.py init
```

### 2. Configuration

Edit `config.json` with your settings:

```json
{
  "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
  "poll_interval": 30,
  "arbitrage_threshold": 0.5,
  "price_change_threshold": 3.0,
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "discord_webhook_url": "YOUR_WEBHOOK_URL"
}
```

**Get Telegram credentials:**
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the token to config
4. Message your bot and visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Find your chat ID in the response

**Get Discord webhook:**
1. Go to your Discord server settings
2. Integrations → Webhooks
3. Create webhook and copy URL

### 3. Start Monitoring

```bash
# Start the bot
python src/bot.py

# Or use OpenClaw skill
clawhub run crypto-alert-bot start-monitoring
```

## 📊 Features

### Multi-Exchange Price Monitoring

Tracks prices across:
- Binance
- Coinbase
- Kraken
- Bybit
- KuCoin

### Arbitrage Detection

Finds price differences between exchanges:

```
🎯 Arbitrage Opportunity!

Buy on BINANCE at $69,450.00
Sell on COINBASE at $69,520.50

Profit: 0.10% ($70.50)
```

**Real example:** If BTC is $100 cheaper on Binance than Coinbase, buy on Binance and sell on Coinbase.

### Whale Tracking

Monitors large transactions (> $1M):

```
🐋 WHALE ALERT

1,500 BTC ($105,035,000)

Type: Exchange Inflow
From: Unknown Wallet
To: Binance

Large inflows to exchanges often precede selling.
```

### Price Change Alerts

Get notified when prices move significantly:

```
📈 UP 5.5%

BTC/USDT current: $73,250.00
Change: +5.5%
Keep monitoring for further movements.
```

## 🎮 OpenClaw Commands

### Initialize
```
clawhub run crypto-alert-bot init
```
Creates configuration file.

### Start Monitoring
```
clawhub run crypto-alert-bot start-monitoring symbols=BTC/USDT,ETH/USDT interval=30
```

### Check Prices
```
clawhub run crypto-alert-bot check-prices symbols=BTC/USDT
```

### Find Arbitrage
```
clawhub run crypto-alert-bot find-arbitrage min_profit=0.5
```

### Check Whales
```
clawhub run crypto-alert-bot check-whales threshold=1000000
```

### Stop Monitoring
```
clawhub run crypto-alert-bot stop-monitoring
```

## ⚙️ Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `symbols` | Trading pairs to monitor | `["BTC/USDT", "ETH/USDT"]` |
| `poll_interval` | Seconds between checks | `30` |
| `arbitrage_threshold` | Min % profit to alert | `0.5` |
| `price_change_threshold` | Min % change to alert | `3.0` |
| `whale_threshold` | Min USD for whale alert | `1000000` |
| `alert_cooldown` | Minutes between duplicate alerts | `15` |

## 💡 Use Cases

### Day Traders
- Get instant arbitrage alerts between exchanges
- Monitor whale movements for early signals
- Track price breakouts in real-time

### Long-term Holders
- Set price alerts for buy/sell targets
- Monitor exchange inflows (selling pressure)
- Stay informed without constant watching

### Arbitrage Traders
- Find price discrepancies automatically
- Compare spreads across 5+ exchanges
- Act on opportunities within seconds

### Researchers
- Collect price data across exchanges
- Track whale wallet patterns
- Analyze market correlations

## 🔧 Advanced Usage

### Custom Callbacks

```python
from src.bot import CryptoAlertBot

def my_custom_handler(alert):
    # Do something with alerts
    print(f"Got alert: {alert.message}")

bot = CryptoAlertBot()
bot.alert_manager.add_callback(my_custom_handler)
bot.start()
```

### Environment Variables

Instead of config.json, you can use env vars:

```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export DISCORD_WEBHOOK_URL="your_webhook"
export POLL_INTERVAL=30
```

### Running as a Service

Create a systemd service for 24/7 monitoring:

```ini
# /etc/systemd/system/crypto-alert-bot.service
[Unit]
Description=Crypto Alert Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/crypto_alert_bot
ExecStart=/usr/bin/python3 src/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📈 Pricing

**$29/month subscription includes:**
- Unlimited symbols
- All exchange monitoring
- Telegram + Discord alerts
- Priority support
- Future updates

**Free tier:**
- 3 symbols max
- Console-only alerts
- Basic features

## 🛡️ Risk Disclaimer

⚠️ **Important:** This tool provides information, not financial advice.

- Past performance doesn't guarantee future results
- Arbitrage opportunities close quickly
- Whale movements don't always predict price action
- Always do your own research

## 🐛 Troubleshooting

### No alerts received
- Check Telegram/Discord credentials
- Verify bot is running: `ps aux | grep bot.py`
- Check logs for errors

### High API rate limits
- Increase `poll_interval` (60+ seconds)
- Reduce number of symbols
- Some exchanges require API keys for high volume

### Missing arbitrage opportunities
- Lower `arbitrage_threshold` to 0.1%
- Ensure all exchanges are accessible from your location
- Check for trading fees (they eat into profits)

## 🤝 Support

- **Documentation:** [GitHub Wiki](https://github.com/yourusername/crypto-alert-bot/wiki)
- **Issues:** [GitHub Issues](https://github.com/yourusername/crypto-alert-bot/issues)
- **Discord:** [Join Server](https://discord.gg/yourinvite)
- **Email:** support@yourdomain.com

## 📜 License

MIT License - See [LICENSE](LICENSE) file

## 🙏 Credits

Built with:
- OpenClaw
- Python 3.8+
- Binance API
- Coinbase API
- Kraken API
- Telegram Bot API

---

**Made with ❤️ for the crypto community**
