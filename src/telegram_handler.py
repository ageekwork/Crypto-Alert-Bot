#!/usr/bin/env python3
"""
Crypto Alert Bot - Telegram Bot Handler (SaaS)
Handles multiple users via Telegram Bot API
"""

import os
import sys
import json
import threading
import time
from datetime import datetime
from typing import Dict, Optional

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.user_manager import UserManager, User, SubscriptionTier
from src.price_monitor import PriceMonitor
from src.alert_manager import AlertManager
from src.whale_tracker import WhaleTracker, WhaleAlertMock


class TelegramBotHandler:
    """
    Handles Telegram bot commands for SaaS multi-user setup
    """
    
    def __init__(self, bot_token: str, user_manager: UserManager):
        self.bot_token = bot_token
        self.user_manager = user_manager
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Alert managers per user
        self.user_alerts: Dict[str, AlertManager] = {}
        
        # Price monitor (shared across users)
        self.price_monitor = PriceMonitor()
        
        # Whale tracker
        self.whale_tracker = WhaleTracker(min_usd_value=1000000)
        
        # Session for API calls
        import requests
        self.session = requests.Session()
    
    def send_message(self, chat_id: str, message: str, parse_mode: str = 'Markdown') -> bool:
        """Send message to Telegram user"""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False
            }
            
            response = self.session.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False
    
    def handle_start(self, chat_id: str, username: str = None) -> str:
        """Handle /start command"""
        # Check if user exists
        user = self.user_manager.get_user_by_telegram(chat_id)
        
        if not user:
            # Create new free user
            user = self.user_manager.create_user(
                telegram_chat_id=chat_id,
                tier=SubscriptionTier.FREE
            )
            if username:
                self.user_manager.update_user(user.user_id, telegram_username=username)
            
            return f"""
🚀 Welcome to Crypto Alert Bot!

I've created your FREE account. You're now monitoring:
{', '.join(user.symbols)}

📊 Your Plan: FREE
• 2 symbols (BTC, ETH)
• 5-minute delay on alerts
• Console-only notifications

💎 Upgrade to PRO for $29/month:
• 8+ symbols
• Real-time alerts (30s)
• Telegram notifications ✅
• Whale tracking
• Priority support

🎮 Commands:
/status - Check your plan
/prices - Current prices
/upgrade - See upgrade options
/settings - Configure alerts
/help - Show all commands

Start monitoring now!
"""
        
        else:
            return f"""
👋 Welcome back, {username or 'Trader'}!

Your current plan: {user.tier.value.upper()}
Symbols monitored: {len(user.symbols)}
Alerts sent: {user.alerts_sent}

Use /status for detailed info.
"""
    
    def handle_status(self, chat_id: str) -> str:
        """Handle /status command"""
        user = self.user_manager.get_user_by_telegram(chat_id)
        
        if not user:
            return "❌ You don't have an account. Send /start to create one."
        
        tier_emoji = {
            SubscriptionTier.FREE: '🆓',
            SubscriptionTier.BASIC: '💚',
            SubscriptionTier.PRO: '💎',
            SubscriptionTier.ENTERPRISE: '👑'
        }
        
        expiry = "Never"
        if user.expires_at:
            expiry_date = datetime.fromisoformat(user.expires_at)
            expiry = expiry_date.strftime('%Y-%m-%d')
        
        return f"""
{tier_emoji.get(user.tier, '•')} Your Status

🎫 Plan: {user.tier.value.upper()}
💰 Monthly Cost: {self._get_plan_price(user.tier)}
📅 Expires: {expiry}

📊 Settings:
• Symbols: {len(user.symbols)}
• Poll interval: {user.poll_interval}s
• Arbitrage threshold: {user.arbitrage_threshold}%
• Price change threshold: {user.price_change_threshold}%
• Whale threshold: ${user.whale_threshold:,.0f}

📈 Stats:
• Alerts sent: {user.alerts_sent}
• Member since: {datetime.fromisoformat(user.created_at).strftime('%Y-%m-%d')}

Use /settings to customize your alerts.
"""
    
    def handle_prices(self, chat_id: str) -> str:
        """Handle /prices command"""
        user = self.user_manager.get_user_by_telegram(chat_id)
        
        if not user:
            return "❌ No account found. Send /start first."
        
        # Fetch prices for user's symbols
        prices = self.price_monitor.fetch_all_prices(user.symbols)
        
        message = "📊 Current Prices\n\n"
        
        for symbol, exchange_data in prices.items():
            if exchange_data:
                avg_price = sum(d.price for d in exchange_data.values()) / len(exchange_data)
                change = next((d.change_24h for d in exchange_data.values() if d.change_24h), 0)
                
                emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                message += f"{emoji} {symbol}: ${avg_price:,.2f} ({change:+.2f}%)\n"
                message += f"   Exchanges: {', '.join(exchange_data.keys())}\n\n"
        
        return message
    
    def handle_upgrade(self, chat_id: str) -> str:
        """Handle /upgrade command"""
        user = self.user_manager.get_user_by_telegram(chat_id)
        
        if not user:
            return "❌ No account found. Send /start first."
        
        current_tier = user.tier
        
        if current_tier == SubscriptionTier.PRO:
            return "💎 You're already on PRO! Thank you for your support! 🙏"
        
        if current_tier == SubscriptionTier.ENTERPRISE:
            return "👑 You're on our highest tier! Contact support for custom needs."
        
        return """
💎 Upgrade Your Plan

🆓 FREE (Current)
• 2 symbols
• 5-minute delay
• $0/month

💚 BASIC - $9/month
• 5 symbols
• 1-minute alerts
• Telegram notifications ✅

💎 PRO - $29/month ⭐ RECOMMENDED
• 8+ symbols
• Real-time (30s) alerts
• Whale tracking
• Priority support

👑 ENTERPRISE - $99/month
• Unlimited symbols
• 10-second updates
• API access
• Custom development

💳 To upgrade:
1. Visit: https://gumroad.com/your-link
2. Subscribe to your plan
3. Forward receipt to @youradmin
4. We'll upgrade you within 1 hour!

Questions? Contact @youradmin
"""
    
    def handle_settings(self, chat_id: str, args: str = None) -> str:
        """Handle /settings command"""
        user = self.user_manager.get_user_by_telegram(chat_id)
        
        if not user:
            return "❌ No account found. Send /start first."
        
        if not args:
            # Show current settings
            return f"""
⚙️ Your Settings

📊 Symbols: {', '.join(user.symbols)}

🔔 Alert Thresholds:
• Price change: {user.price_change_threshold}%
• Arbitrage: {user.arbitrage_threshold}%
• Whale minimum: ${user.whale_threshold:,.0f}

UPDATE: Send /settings threshold 2.0
(Changes alert threshold to 2%)

PRO users can customize all settings!
"""
        
        # Parse settings update
        parts = args.split()
        if len(parts) >= 2:
            setting = parts[0]
            value = parts[1]
            
            try:
                if setting == 'threshold':
                    self.user_manager.update_user(
                        user.user_id,
                        price_change_threshold=float(value)
                    )
                    return f"✅ Price change threshold updated to {value}%"
                
                elif setting == 'arbitrage':
                    self.user_manager.update_user(
                        user.user_id,
                        arbitrage_threshold=float(value)
                    )
                    return f"✅ Arbitrage threshold updated to {value}%"
            
            except ValueError:
                return "❌ Invalid value. Use: /settings threshold 3.0"
        
        return "❌ Usage: /settings threshold 3.0"
    
    def handle_help(self, chat_id: str) -> str:
        """Handle /help command"""
        return """
🎮 Available Commands

📱 General:
/start - Create account or get started
/status - Your plan and stats
/help - Show this help

📊 Monitoring:
/prices - Current prices for your symbols
/arbitrage - Check for opportunities now
/whales - Recent whale movements

⚙️ Settings:
/settings - View your settings
/upgrade - See upgrade options

💎 PRO Commands:
/add BTC/USDT - Add symbol (PRO only)
/remove ETH - Remove symbol

🆘 Support:
/contact - Get help

Happy trading! 🚀
"""
    
    def handle_arbitrage(self, chat_id: str) -> str:
        """Handle /arbitrage command"""
        user = self.user_manager.get_user_by_telegram(chat_id)
        if not user:
            return "❌ No account found. Send /start first."
        
        # Fetch prices for user's symbols
        prices = self.price_monitor.fetch_all_prices(user.symbols)
        
        if not prices:
            return "❌ Could not fetch prices. Try again later."
        
        # Check for arbitrage opportunities
        opportunities = []
        for symbol, exchange_data in prices.items():
            if len(exchange_data) < 2:
                continue
            
            prices_list = [(ex, data.price) for ex, data in exchange_data.items()]
            prices_list.sort(key=lambda x: x[1])
            
            lowest = prices_list[0]
            highest = prices_list[-1]
            
            profit_pct = ((highest[1] - lowest[1]) / lowest[1]) * 100
            
            if profit_pct >= user.arbitrage_threshold:
                opportunities.append({
                    'symbol': symbol,
                    'buy_exchange': lowest[0],
                    'buy_price': lowest[1],
                    'sell_exchange': highest[0],
                    'sell_price': highest[1],
                    'profit_pct': profit_pct
                })
        
        if not opportunities:
            return f"📊 No arbitrage opportunities found (threshold: {user.arbitrage_threshold}%)"
        
        msg = "⚡ **Arbitrage Opportunities**\n\n"
        for opp in opportunities[:5]:
            msg += f"🎯 **{opp['symbol']}**\n"
            msg += f"   Buy: {opp['buy_exchange'].upper()} @ ${opp['buy_price']:,.2f}\n"
            msg += f"   Sell: {opp['sell_exchange'].upper()} @ ${opp['sell_price']:,.2f}\n"
            msg += f"   Profit: **{opp['profit_pct']:.2f}%**\n\n"
        
        return msg
    
    def handle_whales(self, chat_id: str) -> str:
        """Handle /whales command"""
        user = self.user_manager.get_user_by_telegram(chat_id)
        if not user:
            return "❌ No account found. Send /start first."
        
        # Get whale alerts
        alerts = self.whale_tracker.get_bitcoin_whale_transactions(hours=1)
        
        if not alerts:
            return "🐋 No whale movements detected in the last hour."
        
        msg = "🐋 **Recent Whale Movements**\n\n"
        
        for alert in alerts[:5]:
            emoji = '🐋' if alert.amount_usd > 10000000 else '🐳' if alert.amount_usd > 1000000 else '🐟'
            msg += f"{emoji} **{alert.amount:,.2f} {alert.symbol}** (${alert.amount_usd:,.0f})\n"
            msg += f"   Type: {alert.transaction_type.replace('_', ' ').title()}\n"
            msg += f"   From: `{alert.from_address[:15]}...`\n"
            msg += f"   To: `{alert.to_address[:15]}...`\n\n"
        
        return msg
    
    def _get_plan_price(self, tier: SubscriptionTier) -> str:
        """Get price string for tier"""
        prices = {
            SubscriptionTier.FREE: "FREE",
            SubscriptionTier.BASIC: "$9/month",
            SubscriptionTier.PRO: "$29/month",
            SubscriptionTier.ENTERPRISE: "$99/month"
        }
        return prices.get(tier, "Unknown")
    
    def send_alert_to_user(self, user_id: str, alert_message: str):
        """Send alert to specific user"""
        user = self.user_manager.get_user(user_id)
        
        if user and user.telegram_chat_id:
            self.send_message(user.telegram_chat_id, alert_message)
            self.user_manager.increment_alert_count(user_id)


def create_sample_bot():
    """Create a sample Telegram bot for testing"""
    print("""
🤖 To get a Telegram Bot Token:

1. Open Telegram and message @BotFather
2. Send: /newbot
3. Follow prompts to name your bot
4. Copy the token (looks like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
5. Set it as environment variable:
   export TELEGRAM_BOT_TOKEN="your-token-here"

Your bot's URL will be: https://t.me/YourBotName

Users will message it to subscribe!
""")


if __name__ == '__main__':
    create_sample_bot()
