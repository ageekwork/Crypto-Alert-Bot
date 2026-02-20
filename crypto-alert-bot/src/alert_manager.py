#!/usr/bin/env python3
"""
Crypto Alert Bot - Alert Manager
Handles all alert types and notification delivery
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time


class AlertType(Enum):
    PRICE_CHANGE = "price_change"
    ARBITRAGE = "arbitrage"
    WHALE_MOVEMENT = "whale"
    PRICE_TARGET = "price_target"
    POLYMARKET_DIVERGENCE = "polymarket"


@dataclass
class Alert:
    """Represents an alert"""
    id: str
    type: AlertType
    symbol: str
    message: str
    data: Dict
    severity: str  # 'info', 'warning', 'critical'
    timestamp: str
    acknowledged: bool = False


class TelegramNotifier:
    """
    Sends alerts via Telegram Bot
    """
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
    
    def is_configured(self) -> bool:
        return self.bot_token is not None and self.chat_id is not None
    
    def send_message(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """Send a message via Telegram"""
        if not self.is_configured():
            print("⚠️  Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            return False
        
        try:
            import requests
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print("✅ Telegram message sent")
                return True
            else:
                print(f"❌ Telegram error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def send_alert(self, alert: Alert) -> bool:
        """Format and send an alert"""
        emoji_map = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'critical': '🚨'
        }
        
        emoji = emoji_map.get(alert.severity, 'ℹ️')
        
        message = f"""
{emoji} **Crypto Alert Bot** {emoji}

**Type:** {alert.type.value.replace('_', ' ').title()}
**Symbol:** {alert.symbol}
**Severity:** {alert.severity.upper()}
**Time:** {alert.timestamp}

{alert.message}

---
_Alert ID: {alert.id}_
"""
        
        return self.send_message(message)


class DiscordNotifier:
    """
    Sends alerts via Discord Webhook
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
    
    def is_configured(self) -> bool:
        return self.webhook_url is not None
    
    def send_message(self, message: str) -> bool:
        """Send a message via Discord webhook"""
        if not self.is_configured():
            print("⚠️  Discord not configured. Set DISCORD_WEBHOOK_URL")
            return False
        
        try:
            import requests
            
            payload = {
                'content': message,
                'username': 'Crypto Alert Bot'
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                print("✅ Discord message sent")
                return True
            else:
                print(f"❌ Discord error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send Discord message: {e}")
            return False
    
    def send_alert(self, alert: Alert) -> bool:
        """Format and send an alert to Discord"""
        emoji_map = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'critical': '🚨'
        }
        
        emoji = emoji_map.get(alert.severity, 'ℹ️')
        
        message = f"""
{emoji} **Crypto Alert Bot** {emoji}

**Type:** {alert.type.value.replace('_', ' ').title()}
**Symbol:** {alert.symbol}
**Severity:** {alert.severity.upper()}
**Time:** {alert.timestamp}

{alert.message}

---
*Alert ID: {alert.id}*
"""
        
        return self.send_message(message)


class AlertManager:
    """
    Manages all alerts, deduplication, and notification delivery
    """
    
    def __init__(self, 
                 telegram_token: Optional[str] = None,
                 telegram_chat: Optional[str] = None,
                 discord_webhook: Optional[str] = None,
                 cooldown_minutes: int = 15):
        """
        Args:
            cooldown_minutes: Minimum minutes between duplicate alerts
        """
        self.telegram = TelegramNotifier(telegram_token, telegram_chat)
        self.discord = DiscordNotifier(discord_webhook)
        self.cooldown_minutes = cooldown_minutes
        
        # Alert history for deduplication
        self.alert_history: Dict[str, datetime] = {}
        self.sent_alerts: List[Alert] = []
        
        # Callbacks for custom handling
        self.callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable):
        """Add a custom callback for alerts"""
        self.callbacks.append(callback)
    
    def _generate_alert_id(self, alert_type: AlertType, symbol: str, key: str) -> str:
        """Generate unique alert ID"""
        return f"{alert_type.value}_{symbol}_{key}_{datetime.now().strftime('%Y%m%d')}"
    
    def _is_duplicate(self, alert_id: str) -> bool:
        """Check if alert is a duplicate (within cooldown period)"""
        if alert_id not in self.alert_history:
            return False
        
        last_sent = self.alert_history[alert_id]
        cooldown = timedelta(minutes=self.cooldown_minutes)
        
        return datetime.now() - last_sent < cooldown
    
    def send_alert(self, 
                   alert_type: AlertType,
                   symbol: str,
                   message: str,
                   data: Dict,
                   severity: str = 'info',
                   dedup_key: Optional[str] = None) -> bool:
        """
        Send an alert through all configured channels
        
        Args:
            alert_type: Type of alert
            symbol: Cryptocurrency symbol
            message: Alert message
            data: Additional data dict
            severity: 'info', 'warning', or 'critical'
            dedup_key: Key for deduplication (if None, no dedup)
        
        Returns:
            True if alert was sent successfully
        """
        # Generate alert ID
        key = dedup_key or f"{severity}_{int(time.time())}"
        alert_id = self._generate_alert_id(alert_type, symbol, key)
        
        # Check for duplicates
        if dedup_key and self._is_duplicate(alert_id):
            print(f"⏸️  Duplicate alert suppressed: {alert_id}")
            return False
        
        # Create alert
        alert = Alert(
            id=alert_id,
            type=alert_type,
            symbol=symbol,
            message=message,
            data=data,
            severity=severity,
            timestamp=datetime.now().isoformat()
        )
        
        # Track alert
        self.alert_history[alert_id] = datetime.now()
        self.sent_alerts.append(alert)
        
        # Send to all channels
        success = False
        
        if self.telegram.is_configured():
            if self.telegram.send_alert(alert):
                success = True
        
        if self.discord.is_configured():
            if self.discord.send_alert(alert):
                success = True
        
        # Call custom callbacks
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Callback error: {e}")
        
        # Console output if no channels configured
        if not success and not self.callbacks:
            print(f"\n{'='*60}")
            print(f"🚨 ALERT: {alert.type.value.upper()}")
            print(f"{'='*60}")
            print(f"Symbol: {alert.symbol}")
            print(f"Severity: {alert.severity}")
            print(f"Message: {alert.message}")
            print(f"Data: {json.dumps(alert.data, indent=2)}")
            print(f"{'='*60}\n")
            return True
        
        return success
    
    def send_price_alert(self, 
                         symbol: str,
                         current_price: float,
                         change_pct: float,
                         threshold_pct: float = 5.0) -> bool:
        """
        Send a price change alert
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            current_price: Current price
            change_pct: Price change percentage
            threshold_pct: Threshold that triggered the alert
        """
        direction = "📈 UP" if change_pct > 0 else "📉 DOWN"
        severity = 'warning' if abs(change_pct) > threshold_pct * 2 else 'info'
        
        message = f"""
{direction} **{abs(change_pct):.2f}%** in last period

Current Price: ${current_price:,.2f}
Change: {change_pct:+.2f}%
Threshold: {threshold_pct}%

Keep monitoring for further movements.
"""
        
        return self.send_alert(
            alert_type=AlertType.PRICE_CHANGE,
            symbol=symbol,
            message=message,
            data={
                'current_price': current_price,
                'change_pct': change_pct,
                'threshold_pct': threshold_pct
            },
            severity=severity,
            dedup_key=f"price_change_{symbol}"
        )
    
    def send_arbitrage_alert(self, 
                             symbol: str,
                             buy_exchange: str,
                             sell_exchange: str,
                             profit_pct: float,
                             profit_usd: float) -> bool:
        """Send an arbitrage opportunity alert"""
        message = f"""
**Arbitrage Opportunity Detected!**

Buy on **{buy_exchange.upper()}** → Sell on **{sell_exchange.upper()}**

Profit: **{profit_pct:.2f}%** (${profit_usd:.2f})

⚡ Act fast - opportunities close quickly!
"""
        
        return self.send_alert(
            alert_type=AlertType.ARBITRAGE,
            symbol=symbol,
            message=message,
            data={
                'buy_exchange': buy_exchange,
                'sell_exchange': sell_exchange,
                'profit_pct': profit_pct,
                'profit_usd': profit_usd
            },
            severity='critical',
            dedup_key=f"arbitrage_{symbol}_{buy_exchange}_{sell_exchange}"
        )
    
    def send_whale_alert(self, 
                         symbol: str,
                         amount: float,
                         amount_usd: float,
                         tx_type: str,
                         from_addr: str,
                         to_addr: str,
                         tx_hash: str = '') -> bool:
        """Send a whale movement alert"""
        emoji = '🐋' if amount_usd > 10000000 else '🐳' if amount_usd > 1000000 else '🐟'
        
        message = f"""
{emoji} **WHALE MOVEMENT DETECTED** {emoji}

**{amount:,.2f} {symbol}** (${amount_usd:,.0f})

Type: {tx_type.replace('_', ' ').title()}
From: `{from_addr[:20]}...`
To: `{to_addr[:20]}...`
Tx: `{tx_hash[:16]}...`

Large movements can indicate upcoming volatility.
"""
        
        severity = 'critical' if amount_usd > 10000000 else 'warning'
        
        # Use tx_hash for deduplication if available, otherwise use from+to+amount
        dedup_key = f"whale_{tx_hash}" if tx_hash else f"whale_{from_addr}_{to_addr}_{amount}"
        
        return self.send_alert(
            alert_type=AlertType.WHALE_MOVEMENT,
            symbol=symbol,
            message=message,
            data={
                'amount': amount,
                'amount_usd': amount_usd,
                'tx_type': tx_type,
                'from': from_addr,
                'to': to_addr,
                'tx_hash': tx_hash
            },
            severity=severity,
            dedup_key=dedup_key
        )
    
    def get_alert_stats(self) -> Dict:
        """Get statistics about sent alerts"""
        total = len(self.sent_alerts)
        by_type = {}
        by_severity = {}
        
        for alert in self.sent_alerts:
            by_type[alert.type.value] = by_type.get(alert.type.value, 0) + 1
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
        
        return {
            'total_alerts': total,
            'by_type': by_type,
            'by_severity': by_severity,
            'last_24h': len([a for a in self.sent_alerts 
                           if datetime.fromisoformat(a.timestamp) > datetime.now() - timedelta(days=1)])
        }


if __name__ == '__main__':
    print("Testing Alert Manager")
    print("=" * 60)
    
    # Create manager (no notifications - console only)
    manager = AlertManager()
    
    # Test different alert types
    print("\n1. Testing Price Alert:")
    manager.send_price_alert(
        symbol='BTC/USDT',
        current_price=69500.50,
        change_pct=5.5,
        threshold_pct=5.0
    )
    
    print("\n2. Testing Arbitrage Alert:")
    manager.send_arbitrage_alert(
        symbol='ETH/USDT',
        buy_exchange='binance',
        sell_exchange='coinbase',
        profit_pct=1.2,
        profit_usd=24.50
    )
    
    print("\n3. Testing Whale Alert:")
    manager.send_whale_alert(
        symbol='BTC',
        amount=1500.0,
        amount_usd=105000000,
        tx_type='exchange_in',
        from_addr='1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
        to_addr='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh'
    )
    
    print("\n4. Statistics:")
    stats = manager.get_alert_stats()
    print(f"   Total alerts: {stats['total_alerts']}")
    print(f"   By type: {stats['by_type']}")
    print(f"   By severity: {stats['by_severity']}")
