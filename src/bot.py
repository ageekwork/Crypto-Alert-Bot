#!/usr/bin/env python3
"""
Crypto Alert Bot - Main Controller
Orchestrates all monitoring and alert systems
"""

import json
import os
import time
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional
import threading

from price_monitor import PriceMonitor
from whale_tracker import WhaleTracker, WhaleAlertMock
from alert_manager import AlertManager, AlertType


class CryptoAlertBot:
    """
    Main bot controller that coordinates all monitoring systems
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the bot with configuration
        
        Args:
            config_path: Path to config file (optional)
        """
        self.config = self._load_config(config_path)
        self.running = False
        
        # Initialize components
        self.price_monitor = PriceMonitor(
            poll_interval=self.config.get('poll_interval', 30)
        )
        
        self.whale_tracker = WhaleAlertMock(
            min_usd_value=self.config.get('whale_threshold', 1000000)
        )
        
        self.alert_manager = AlertManager(
            telegram_token=self.config.get('telegram_bot_token'),
            telegram_chat=self.config.get('telegram_chat_id'),
            discord_webhook=self.config.get('discord_webhook_url'),
            cooldown_minutes=self.config.get('alert_cooldown', 15)
        )
        
        # Monitoring settings
        self.symbols = self.config.get('symbols', ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'])
        self.arbitrage_threshold = self.config.get('arbitrage_threshold', 0.5)  # 0.5%
        self.price_change_threshold = self.config.get('price_change_threshold', 3.0)  # 3%
        
        # Previous prices for change detection
        self.previous_prices: Dict[str, float] = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or environment"""
        config = {
            # Default settings
            'poll_interval': 30,
            'arbitrage_threshold': 0.5,
            'price_change_threshold': 3.0,
            'whale_threshold': 1000000,
            'alert_cooldown': 15,
            'symbols': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
        }
        
        # Load from file if provided
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
                print(f"✅ Config loaded from {config_path}")
            except Exception as e:
                print(f"⚠️  Error loading config: {e}")
        
        # Override with environment variables
        env_mappings = {
            'TELEGRAM_BOT_TOKEN': 'telegram_bot_token',
            'TELEGRAM_CHAT_ID': 'telegram_chat_id',
            'DISCORD_WEBHOOK_URL': 'discord_webhook_url',
            'POLL_INTERVAL': ('poll_interval', int),
            'ARBITRAGE_THRESHOLD': ('arbitrage_threshold', float),
            'PRICE_CHANGE_THRESHOLD': ('price_change_threshold', float),
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                if isinstance(config_key, tuple):
                    config_key, converter = config_key
                    config[config_key] = converter(value)
                else:
                    config[config_key] = value
        
        return config
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\n\n🛑 Shutdown signal received. Stopping bot...")
        self.stop()
        sys.exit(0)
    
    def _check_price_changes(self, prices: Dict):
        """Check for significant price changes"""
        for symbol, exchange_data in prices.items():
            if not exchange_data:
                continue
            
            # Get average price across exchanges
            avg_price = sum(d.price for d in exchange_data.values()) / len(exchange_data)
            
            if symbol in self.previous_prices:
                old_price = self.previous_prices[symbol]
                change_pct = ((avg_price - old_price) / old_price) * 100
                
                if abs(change_pct) >= self.price_change_threshold:
                    self.alert_manager.send_price_alert(
                        symbol=symbol,
                        current_price=avg_price,
                        change_pct=change_pct,
                        threshold_pct=self.price_change_threshold
                    )
            
            self.previous_prices[symbol] = avg_price
    
    def _check_arbitrage(self):
        """Check for arbitrage opportunities"""
        opportunities = self.price_monitor.find_arbitrage(
            self.symbols,
            min_profit_pct=self.arbitrage_threshold
        )
        
        for opp in opportunities:
            self.alert_manager.send_arbitrage_alert(
                symbol=opp.symbol,
                buy_exchange=opp.buy_exchange,
                sell_exchange=opp.sell_exchange,
                profit_pct=opp.profit_pct,
                profit_usd=opp.profit_usd
            )
    
    def _check_whale_movements(self):
        """Check for whale transactions"""
        alerts = self.whale_tracker.get_bitcoin_whale_transactions(hours=1)
        
        for alert in alerts:
            self.alert_manager.send_whale_alert(
                symbol=alert.symbol,
                amount=alert.amount,
                amount_usd=alert.amount_usd,
                tx_type=alert.transaction_type,
                from_addr=alert.from_address,
                to_addr=alert.to_address
            )
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        print(f"\n🔍 Starting monitoring loop")
        print(f"   Symbols: {', '.join(self.symbols)}")
        print(f"   Poll interval: {self.config.get('poll_interval', 30)}s")
        print(f"   Arbitrage threshold: {self.arbitrage_threshold}%")
        print(f"   Price change threshold: {self.price_change_threshold}%")
        print(f"   Whale threshold: ${self.config.get('whale_threshold', 1000000):,}")
        
        iteration = 0
        
        while self.running:
            try:
                iteration += 1
                print(f"\n{'='*60}")
                print(f"🔄 Iteration {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                # Fetch prices
                print("\n📊 Fetching prices...")
                prices = self.price_monitor.fetch_all_prices(self.symbols)
                
                # Display prices
                for symbol, exchange_data in prices.items():
                    if exchange_data:
                        print(f"\n{symbol}:")
                        for exchange, data in exchange_data.items():
                            print(f"  {exchange:10}: ${data.price:,.2f}")
                
                # Check for price changes
                print("\n📈 Checking price changes...")
                self._check_price_changes(prices)
                
                # Check for arbitrage
                print("\n🎯 Checking arbitrage opportunities...")
                self._check_arbitrage()
                
                # Check for whale movements (every 5 iterations to save API calls)
                if iteration % 5 == 0:
                    print("\n🐋 Checking whale movements...")
                    self._check_whale_movements()
                
                # Print stats
                stats = self.alert_manager.get_alert_stats()
                print(f"\n📊 Stats: {stats['total_alerts']} alerts sent")
                
                # Wait for next iteration
                time.sleep(self.config.get('poll_interval', 30))
                
            except Exception as e:
                print(f"\n❌ Error in monitoring loop: {e}")
                time.sleep(5)  # Short delay on error
    
    def start(self):
        """Start the bot"""
        print("\n" + "="*60)
        print("🚀 Crypto Alert Bot Starting")
        print("="*60)
        
        # Check configuration
        print("\n📋 Configuration:")
        print(f"   Telegram: {'✅ Configured' if self.alert_manager.telegram.is_configured() else '⚠️  Not configured'}")
        print(f"   Discord: {'✅ Configured' if self.alert_manager.discord.is_configured() else '⚠️  Not configured'}")
        
        self.running = True
        
        # Start monitoring in background thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        print("\n✅ Bot started successfully!")
        print("   Press Ctrl+C to stop\n")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the bot"""
        print("\n🛑 Stopping bot...")
        self.running = False
        
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
        
        print("✅ Bot stopped")
        
        # Print final stats
        stats = self.alert_manager.get_alert_stats()
        print(f"\n📊 Final Statistics:")
        print(f"   Total alerts sent: {stats['total_alerts']}")
        print(f"   By type: {stats['by_type']}")
        print(f"   By severity: {stats['by_severity']}")


def create_sample_config():
    """Create a sample configuration file"""
    config = {
        "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"],
        "poll_interval": 30,
        "arbitrage_threshold": 0.5,
        "price_change_threshold": 3.0,
        "whale_threshold": 1000000,
        "alert_cooldown": 15,
        "telegram_bot_token": "YOUR_BOT_TOKEN_HERE",
        "telegram_chat_id": "YOUR_CHAT_ID_HERE",
        "discord_webhook_url": "YOUR_WEBHOOK_URL_HERE"
    }
    
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Sample config created: config.json")
    print("   Edit it with your API keys and settings")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Alert Bot')
    parser.add_argument('--config', '-c', help='Path to config file')
    parser.add_argument('--init', action='store_true', help='Create sample config file')
    
    args = parser.parse_args()
    
    if args.init:
        create_sample_config()
    else:
        # Start the bot
        bot = CryptoAlertBot(config_path=args.config)
        bot.start()
