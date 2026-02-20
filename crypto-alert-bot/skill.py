#!/usr/bin/env python3
"""
Crypto Alert Bot - OpenClaw Skill Integration
Allows the bot to be used as an OpenClaw skill
"""

import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from bot import CryptoAlertBot, create_sample_config
from price_monitor import PriceMonitor
from alert_manager import AlertManager


class OpenClawSkill:
    """
    OpenClaw Skill wrapper for Crypto Alert Bot
    """
    
    def __init__(self):
        self.bot = None
        self.price_monitor = None
        self.alert_manager = None
    
    def init(self):
        """Initialize the skill - create config if needed"""
        config_path = Path('config.json')
        if not config_path.exists():
            create_sample_config()
            return {
                'status': 'initialized',
                'message': 'Created config.json. Please edit it with your API keys.',
                'next_steps': [
                    'Edit config.json with your Telegram/Discord credentials',
                    'Run "start-monitoring" to begin'
                ]
            }
        else:
            return {
                'status': 'ready',
                'message': 'Crypto Alert Bot is configured and ready',
                'config_exists': True
            }
    
    def start_monitoring(self, symbols=None, interval=None):
        """Start monitoring cryptocurrencies"""
        try:
            self.bot = CryptoAlertBot()
            
            # Override with provided params if given
            if symbols:
                self.bot.symbols = symbols if isinstance(symbols, list) else symbols.split(',')
            if interval:
                self.bot.config['poll_interval'] = int(interval)
            
            # Start in background
            import threading
            self.bot.running = True
            thread = threading.Thread(target=self.bot._monitoring_loop)
            thread.daemon = True
            thread.start()
            
            return {
                'status': 'started',
                'message': f'Monitoring started for: {", ".join(self.bot.symbols)}',
                'symbols': self.bot.symbols,
                'interval': self.bot.config.get('poll_interval', 30)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to start monitoring: {str(e)}'
            }
    
    def stop_monitoring(self):
        """Stop the monitoring"""
        if self.bot:
            self.bot.stop()
            return {
                'status': 'stopped',
                'message': 'Monitoring stopped',
                'stats': self.bot.alert_manager.get_alert_stats()
            }
        else:
            return {
                'status': 'not_running',
                'message': 'Bot is not currently running'
            }
    
    def check_prices(self, symbols=None):
        """Check current prices across exchanges"""
        try:
            monitor = PriceMonitor()
            symbols = symbols or ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
            if isinstance(symbols, str):
                symbols = symbols.split(',')
            
            prices = monitor.fetch_all_prices(symbols)
            
            result = {}
            for symbol, exchange_data in prices.items():
                result[symbol] = {
                    exchange: {
                        'price': data.price,
                        'bid': data.bid,
                        'ask': data.ask,
                        'change_24h': data.change_24h
                    }
                    for exchange, data in exchange_data.items()
                }
            
            return {
                'status': 'success',
                'prices': result,
                'timestamp': json.dumps(datetime.now().isoformat())
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def find_arbitrage(self, symbols=None, min_profit=0.5):
        """Find arbitrage opportunities"""
        try:
            monitor = PriceMonitor()
            symbols = symbols or ['BTC/USDT', 'ETH/USDT']
            if isinstance(symbols, str):
                symbols = symbols.split(',')
            
            # Fetch prices first
            monitor.fetch_all_prices(symbols)
            
            # Find opportunities
            opportunities = monitor.find_arbitrage(symbols, min_profit_pct=float(min_profit))
            
            return {
                'status': 'success',
                'opportunities': [
                    {
                        'symbol': opp.symbol,
                        'buy_exchange': opp.buy_exchange,
                        'sell_exchange': opp.sell_exchange,
                        'buy_price': opp.buy_price,
                        'sell_price': opp.sell_price,
                        'profit_pct': opp.profit_pct,
                        'profit_usd': opp.profit_usd
                    }
                    for opp in opportunities
                ],
                'count': len(opportunities)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def check_whales(self, threshold=1000000):
        """Check recent whale movements"""
        try:
            from whale_tracker import WhaleAlertMock
            
            tracker = WhaleAlertMock(min_usd_value=float(threshold))
            alerts = tracker.get_bitcoin_whale_transactions(hours=1)
            
            return {
                'status': 'success',
                'whales': [
                    {
                        'symbol': alert.symbol,
                        'amount': alert.amount,
                        'amount_usd': alert.amount_usd,
                        'type': alert.transaction_type,
                        'from': alert.from_address[:20] + '...',
                        'to': alert.to_address[:20] + '...',
                        'timestamp': alert.timestamp
                    }
                    for alert in alerts
                ],
                'count': len(alerts)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def test_alert(self, channel='telegram'):
        """Send a test alert"""
        try:
            manager = AlertManager()
            
            if channel == 'telegram':
                success = manager.telegram.send_message("🧪 Test alert from Crypto Alert Bot!")
            elif channel == 'discord':
                success = manager.discord.send_message("🧪 Test alert from Crypto Alert Bot!")
            else:
                return {'status': 'error', 'message': f'Unknown channel: {channel}'}
            
            return {
                'status': 'success' if success else 'failed',
                'message': f'Test alert {"sent" if success else "failed"} to {channel}'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }


# Create skill instance
skill = OpenClawSkill()

# Export functions for OpenClaw
if __name__ == '__main__':
    import sys
    from datetime import datetime
    
    # Simple CLI for testing
    if len(sys.argv) < 2:
        print("Usage: python skill.py <command> [args]")
        print("Commands: init, start, stop, prices, arbitrage, whales, test")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'init':
        print(json.dumps(skill.init(), indent=2))
    elif cmd == 'start':
        symbols = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(skill.start_monitoring(symbols), indent=2))
    elif cmd == 'stop':
        print(json.dumps(skill.stop_monitoring(), indent=2))
    elif cmd == 'prices':
        symbols = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(skill.check_prices(symbols), indent=2))
    elif cmd == 'arbitrage':
        print(json.dumps(skill.find_arbitrage(), indent=2))
    elif cmd == 'whales':
        print(json.dumps(skill.check_whales(), indent=2))
    elif cmd == 'test':
        channel = sys.argv[2] if len(sys.argv) > 2 else 'telegram'
        print(json.dumps(skill.test_alert(channel), indent=2))
    else:
        print(f"Unknown command: {cmd}")
