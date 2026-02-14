#!/usr/bin/env python3
"""
Crypto Alert Bot - SaaS Main Entry Point
Multi-tenant service running all user monitoring
"""

import os
import sys
import time
import threading
import signal
from datetime import datetime
from typing import Dict, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from user_manager import UserManager, User, SubscriptionTier
from telegram_handler import TelegramBotHandler
from price_monitor import PriceMonitor
from alert_manager import AlertManager
from whale_tracker import WhaleAlertMock


class SaaSService:
    """
    Main SaaS service that handles all users
    """
    
    def __init__(self):
        print("="*70)
        print("🚀 Crypto Alert Bot - SaaS Service Starting")
        print("="*70)
        
        # Check for bot token
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            print("\n❌ Error: TELEGRAM_BOT_TOKEN not set")
            print("   Set it with: export TELEGRAM_BOT_TOKEN='your-token'")
            print("   Or create .env file with TELEGRAM_BOT_TOKEN=...")
            sys.exit(1)
        
        # Initialize components
        print("\n📦 Initializing components...")
        
        self.user_manager = UserManager(data_dir='data')
        self.telegram = TelegramBotHandler(self.bot_token, self.user_manager)
        self.price_monitor = PriceMonitor()
        
        # Running state
        self.running = False
        self.monitor_thread = None
        self.bot_thread = None
        
        # Track user alert managers
        self.user_alert_managers: Dict[str, AlertManager] = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("✅ Service initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\n🛑 Shutdown signal received...")
        self.stop()
        sys.exit(0)
    
    def _get_or_create_alert_manager(self, user: User) -> AlertManager:
        """Get or create alert manager for user"""
        if user.user_id not in self.user_alert_managers:
            manager = AlertManager(
                telegram_token=os.getenv('TELEGRAM_BOT_TOKEN'),
                telegram_chat=user.telegram_chat_id,
                cooldown_minutes=15
            )
            self.user_alert_managers[user.user_id] = manager
        
        return self.user_alert_managers[user.user_id]
    
    def _check_price_changes_for_user(self, user: User, prices: Dict):
        """Check price changes for specific user"""
        alert_manager = self._get_or_create_alert_manager(user)
        
        for symbol, exchange_data in prices.items():
            if symbol not in user.symbols:
                continue
            
            if not exchange_data:
                continue
            
            # Calculate average price
            avg_price = sum(d.price for d in exchange_data.values()) / len(exchange_data)
            
            # Get previous price for this user
            previous_key = f"{user.user_id}_{symbol}"
            previous_price = self.price_monitor.previous_prices.get(previous_key)
            
            if previous_price:
                change_pct = ((avg_price - previous_price) / previous_price) * 100
                
                if abs(change_pct) >= user.price_change_threshold:
                    # Send alert
                    alert_manager.send_price_alert(
                        symbol=symbol,
                        current_price=avg_price,
                        change_pct=change_pct,
                        threshold_pct=user.price_change_threshold
                    )
                    
                    self.user_manager.increment_alert_count(user.user_id)
            
            # Store for next check
            self.price_monitor.previous_prices[previous_key] = avg_price
    
    def _check_arbitrage_for_user(self, user: User):
        """Check arbitrage for specific user"""
        if user.tier == SubscriptionTier.FREE:
            return  # Free users don't get arbitrage alerts
        
        alert_manager = self._get_or_create_alert_manager(user)
        
        opportunities = self.price_monitor.find_arbitrage(
            user.symbols,
            min_profit_pct=user.arbitrage_threshold
        )
        
        for opp in opportunities:
            alert_manager.send_arbitrage_alert(
                symbol=opp.symbol,
                buy_exchange=opp.buy_exchange,
                sell_exchange=opp.sell_exchange,
                profit_pct=opp.profit_pct,
                profit_usd=opp.profit_usd
            )
            
            self.user_manager.increment_alert_count(user.user_id)
    
    def _check_whales_for_user(self, user: User, iteration: int):
        """Check whale movements for specific user"""
        # Only PRO and above get whale alerts
        if user.tier in [SubscriptionTier.FREE, SubscriptionTier.BASIC]:
            return
        
        # Check every 5 iterations (to save API calls)
        if iteration % 5 != 0:
            return
        
        tracker = WhaleAlertMock(min_usd_value=user.whale_threshold)
        alerts = tracker.get_bitcoin_whale_transactions(hours=1)
        
        if alerts:
            alert_manager = self._get_or_create_alert_manager(user)
            
            for alert in alerts:
                alert_manager.send_whale_alert(
                    symbol=alert.symbol,
                    amount=alert.amount,
                    amount_usd=alert.amount_usd,
                    tx_type=alert.transaction_type,
                    from_addr=alert.from_address,
                    to_addr=alert.to_address
                )
                
                self.user_manager.increment_alert_count(user.user_id)
    
    def _monitoring_loop(self):
        """Main monitoring loop for all users"""
        print("\n🔍 Starting monitoring loop...")
        
        iteration = 0
        
        while self.running:
            try:
                iteration += 1
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Get all active users
                users = self.user_manager.get_active_users()
                
                if users:
                    print(f"\n{'='*70}")
                    print(f"🔄 Iteration {iteration} | {now} | {len(users)} users")
                    print(f"{'='*70}")
                    
                    # Get unique symbols from all users
                    all_symbols = set()
                    for user in users:
                        all_symbols.update(user.symbols)
                    
                    all_symbols = list(all_symbols)
                    
                    # Fetch prices once for all symbols
                    print(f"\n📊 Fetching prices for {len(all_symbols)} symbols...")
                    prices = self.price_monitor.fetch_all_prices(all_symbols)
                    
                    # Process each user
                    for user in users:
                        # Check user's poll interval
                        # (simplified - should track per-user timing)
                        
                        print(f"\n  👤 {user.user_id[:8]}... ({user.tier.value})")
                        
                        # Check price changes
                        self._check_price_changes_for_user(user, prices)
                        
                        # Check arbitrage
                        self._check_arbitrage_for_user(user)
                        
                        # Check whales
                        self._check_whales_for_user(user, iteration)
                    
                    # Save user data periodically
                    if iteration % 10 == 0:
                        self.user_manager.save_all()
                        print(f"\n💾 User data saved")
                else:
                    print(f"\n⏳ {now} - No active users yet")
                
                # Check for expired subscriptions every hour
                if iteration % 120 == 0:  # Every ~1 hour (assuming 30s interval)
                    expired = self.user_manager.deactivate_expired()
                    if expired:
                        print(f"\n⏸️  Downgraded {len(expired)} expired subscriptions")
                
                # Wait for next iteration
                time.sleep(30)  # Base interval - could optimize per-user
                
            except Exception as e:
                print(f"\n❌ Error in monitoring loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)
    
    def _bot_command_loop(self):
        """Handle Telegram bot commands"""
        print("\n🤖 Starting Telegram bot command handler...")
        
        import requests
        
        offset = 0
        
        while self.running:
            try:
                # Get updates from Telegram
                url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
                params = {'offset': offset, 'limit': 10}
                
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('ok') and data.get('result'):
                        for update in data['result']:
                            # Update offset
                            offset = update['update_id'] + 1
                            
                            # Process message
                            if 'message' in update:
                                message = update['message']
                                chat_id = str(message['chat']['id'])
                                username = message['chat'].get('username', 'Unknown')
                                text = message.get('text', '')
                                
                                print(f"\n📨 Message from {username}: {text[:50]}")
                                
                                # Handle commands
                                response_text = self._handle_command(chat_id, username, text)
                                
                                if response_text:
                                    self.telegram.send_message(chat_id, response_text)
                
                time.sleep(1)  # Check for messages every second
                
            except Exception as e:
                print(f"\n❌ Error in bot loop: {e}")
                time.sleep(5)
    
    def _handle_command(self, chat_id: str, username: str, text: str) -> str:
        """Handle incoming Telegram command"""
        text = text.lower().strip()
        
        if text == '/start':
            return self.telegram.handle_start(chat_id, username)
        
        elif text == '/status':
            return self.telegram.handle_status(chat_id)
        
        elif text == '/prices':
            return self.telegram.handle_prices(chat_id)
        
        elif text == '/upgrade':
            return self.telegram.handle_upgrade(chat_id)
        
        elif text.startswith('/settings'):
            args = text[10:].strip() if len(text) > 10 else None
            return self.telegram.handle_settings(chat_id, args)
        
        elif text == '/help':
            return self.telegram.handle_help(chat_id)
        
        elif text.startswith('/'):
            return "❓ Unknown command. Send /help for available commands."
        
        # Handle plain messages (could be email verification, etc.)
        return None
    
    def start(self):
        """Start the SaaS service"""
        print("\n" + "="*70)
        print("🟢 Starting all services...")
        print("="*70)
        
        self.running = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("✅ Monitoring service started")
        
        # Start bot command thread
        self.bot_thread = threading.Thread(target=self._bot_command_loop)
        self.bot_thread.daemon = True
        self.bot_thread.start()
        print("✅ Telegram bot started")
        
        # Print status
        print("\n" + "="*70)
        print("🚀 SaaS Service Running!")
        print("="*70)
        
        stats = self.user_manager.get_stats()
        print(f"\n📊 Current Stats:")
        print(f"   Total users: {stats['total_users']}")
        print(f"   By tier: {stats['by_tier']}")
        print(f"   Monthly revenue: ${stats['monthly_recurring_revenue']}")
        print(f"   Total alerts sent: {stats['total_alerts_sent']}")
        
        print(f"\n🤖 Bot URL: https://t.me/{self._get_bot_username()}")
        print("\nPress Ctrl+C to stop\n")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the service"""
        print("\n🛑 Stopping service...")
        self.running = False
        
        # Wait for threads
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.bot_thread:
            self.bot_thread.join(timeout=5)
        
        # Save data
        self.user_manager.save_all()
        
        print("✅ Service stopped")
    
    def _get_bot_username(self) -> str:
        """Get bot username from Telegram"""
        import requests
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data['result'].get('username', 'your_bot')
        except:
            pass
        return 'your_bot'


def main():
    """Main entry point"""
    service = SaaSService()
    service.start()


if __name__ == '__main__':
    main()
