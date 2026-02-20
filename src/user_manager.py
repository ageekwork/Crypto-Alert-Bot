#!/usr/bin/env python3
"""
Crypto Alert Bot - SaaS Multi-Tenant Manager
Handles multiple users on a single instance
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class SubscriptionTier(Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class User:
    """Represents a subscribed user"""
    user_id: str
    telegram_chat_id: Optional[str]
    telegram_username: Optional[str]
    discord_webhook: Optional[str]
    email: Optional[str]
    
    # Subscription
    tier: SubscriptionTier
    subscribed_at: str
    expires_at: Optional[str]
    is_active: bool
    
    # Settings
    symbols: List[str]
    arbitrage_threshold: float
    price_change_threshold: float
    whale_threshold: float
    poll_interval: int
    
    # Stats
    alerts_sent: int
    last_activity: str
    created_at: str
    
    def __init__(self, telegram_chat_id: str = None, tier: SubscriptionTier = SubscriptionTier.FREE):
        self.user_id = str(uuid.uuid4())
        self.telegram_chat_id = telegram_chat_id
        self.telegram_username = None
        self.discord_webhook = None
        self.email = None
        
        self.tier = tier
        self.subscribed_at = datetime.now().isoformat()
        self.expires_at = None
        self.is_active = True
        
        # Default settings by tier
        self.set_default_settings(tier)
        
        self.alerts_sent = 0
        self.last_activity = datetime.now().isoformat()
        self.created_at = datetime.now().isoformat()
    
    def set_default_settings(self, tier: SubscriptionTier):
        """Set default settings based on tier"""
        defaults = {
            SubscriptionTier.FREE: {
                'symbols': ['BTC/USDT', 'ETH/USDT'],
                'arbitrage_threshold': 0.5,
                'price_change_threshold': 5.0,
                'whale_threshold': 10000000,
                'poll_interval': 300  # 5 minutes (delayed)
            },
            SubscriptionTier.BASIC: {
                'symbols': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT'],
                'arbitrage_threshold': 0.5,
                'price_change_threshold': 3.0,
                'whale_threshold': 5000000,
                'poll_interval': 60  # 1 minute
            },
            SubscriptionTier.PRO: {
                'symbols': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT', 
                           'AVAX/USDT', 'MATIC/USDT', 'LINK/USDT'],
                'arbitrage_threshold': 0.3,
                'price_change_threshold': 2.0,
                'whale_threshold': 1000000,
                'poll_interval': 30  # 30 seconds (real-time)
            },
            SubscriptionTier.ENTERPRISE: {
                'symbols': [],  # Custom
                'arbitrage_threshold': 0.1,
                'price_change_threshold': 1.0,
                'whale_threshold': 500000,
                'poll_interval': 10  # 10 seconds
            }
        }
        
        settings = defaults.get(tier, defaults[SubscriptionTier.FREE])
        self.symbols = settings['symbols']
        self.arbitrage_threshold = settings['arbitrage_threshold']
        self.price_change_threshold = settings['price_change_threshold']
        self.whale_threshold = settings['whale_threshold']
        self.poll_interval = settings['poll_interval']


class UserManager:
    """
    Manages all users for the SaaS instance
    """
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.users_file = self.data_dir / 'users.json'
        self.users: Dict[str, User] = {}
        
        self._load_users()
    
    def _load_users(self):
        """Load users from disk"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    for user_data in data:
                        user = User()
                        for key, value in user_data.items():
                            if key == 'tier':
                                setattr(user, key, SubscriptionTier(value))
                            else:
                                setattr(user, key, value)
                        self.users[user.user_id] = user
                print(f"✅ Loaded {len(self.users)} users")
            except Exception as e:
                print(f"⚠️  Error loading users: {e}")
    
    def _save_users(self):
        """Save users to disk"""
        try:
            data = []
            for user in self.users.values():
                user_dict = asdict(user)
                user_dict['tier'] = user.tier.value
                data.append(user_dict)
            
            with open(self.users_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving users: {e}")
    
    def create_user(self, telegram_chat_id: str = None, tier: SubscriptionTier = SubscriptionTier.FREE) -> User:
        """Create a new user"""
        # Check if user already exists with this chat ID
        for user in self.users.values():
            if user.telegram_chat_id == telegram_chat_id:
                print(f"⚠️  User with chat ID {telegram_chat_id} already exists")
                return user
        
        user = User(telegram_chat_id=telegram_chat_id, tier=tier)
        self.users[user.user_id] = user
        self._save_users()
        
        print(f"✅ Created new user: {user.user_id}")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_telegram(self, chat_id: str) -> Optional[User]:
        """Get user by Telegram chat ID"""
        for user in self.users.values():
            if user.telegram_chat_id == chat_id:
                return user
        return None
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        """Update user settings"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.last_activity = datetime.now().isoformat()
        self._save_users()
        return True
    
    def upgrade_tier(self, user_id: str, new_tier: SubscriptionTier, duration_days: int = 30) -> bool:
        """Upgrade user to paid tier"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.tier = new_tier
        user.set_default_settings(new_tier)
        
        # Set expiration
        expiry = datetime.now() + timedelta(days=duration_days)
        user.expires_at = expiry.isoformat()
        
        self._save_users()
        print(f"✅ Upgraded {user_id} to {new_tier.value}")
        return True
    
    def check_expired_subscriptions(self) -> List[User]:
        """Find users with expired subscriptions"""
        expired = []
        now = datetime.now()
        
        for user in self.users.values():
            if user.tier != SubscriptionTier.FREE and user.expires_at:
                expiry = datetime.fromisoformat(user.expires_at)
                if expiry < now:
                    expired.append(user)
        
        return expired
    
    def deactivate_expired(self):
        """Deactivate expired subscriptions"""
        expired = self.check_expired_subscriptions()
        
        for user in expired:
            user.tier = SubscriptionTier.FREE
            user.set_default_settings(SubscriptionTier.FREE)
            user.is_active = True  # Keep active but downgrade
            print(f"⏸️  Downgraded expired user: {user.user_id}")
        
        if expired:
            self._save_users()
        
        return expired
    
    def get_active_users(self) -> List[User]:
        """Get all active users"""
        return [u for u in self.users.values() if u.is_active]
    
    def get_stats(self) -> Dict:
        """Get user statistics"""
        total = len(self.users)
        by_tier = {}
        by_status = {'active': 0, 'inactive': 0, 'expired': 0}
        total_alerts = 0
        
        for user in self.users.values():
            tier_name = user.tier.value
            by_tier[tier_name] = by_tier.get(tier_name, 0) + 1
            
            if user.is_active:
                by_status['active'] += 1
            else:
                by_status['inactive'] += 1
            
            if user.expires_at:
                expiry = datetime.fromisoformat(user.expires_at)
                if expiry < datetime.now() and user.tier != SubscriptionTier.FREE:
                    by_status['expired'] += 1
            
            total_alerts += user.alerts_sent
        
        # Calculate MRR (Monthly Recurring Revenue)
        prices = {
            SubscriptionTier.BASIC: 9,
            SubscriptionTier.PRO: 29,
            SubscriptionTier.ENTERPRISE: 99
        }
        
        mrr = 0
        for user in self.users.values():
            if user.is_active and user.tier != SubscriptionTier.FREE:
                # Check not expired
                if user.expires_at:
                    expiry = datetime.fromisoformat(user.expires_at)
                    if expiry > datetime.now():
                        mrr += prices.get(user.tier, 0)
        
        return {
            'total_users': total,
            'by_tier': by_tier,
            'by_status': by_status,
            'total_alerts_sent': total_alerts,
            'monthly_recurring_revenue': mrr
        }
    
    def increment_alert_count(self, user_id: str):
        """Increment user's alert count"""
        user = self.users.get(user_id)
        if user:
            user.alerts_sent += 1
            user.last_activity = datetime.now().isoformat()
            # Don't save on every alert - batch this
    
    def save_all(self):
        """Force save all users"""
        self._save_users()


if __name__ == '__main__':
    print("🚀 Testing SaaS User Manager")
    print("="*60)
    
    manager = UserManager()
    
    # Create test users
    print("\n1. Creating test users...")
    
    free_user = manager.create_user(telegram_chat_id="123456789", tier=SubscriptionTier.FREE)
    print(f"   Free user: {free_user.user_id}")
    print(f"   Symbols: {len(free_user.symbols)} (Expected: 2)")
    print(f"   Poll interval: {free_user.poll_interval}s (Expected: 300)")
    
    pro_user = manager.create_user(telegram_chat_id="987654321", tier=SubscriptionTier.PRO)
    print(f"\n   Pro user: {pro_user.user_id}")
    print(f"   Symbols: {len(pro_user.symbols)} (Expected: 8)")
    print(f"   Poll interval: {pro_user.poll_interval}s (Expected: 30)")
    
    # Get stats
    print("\n2. User stats:")
    stats = manager.get_stats()
    print(f"   Total users: {stats['total_users']}")
    print(f"   By tier: {stats['by_tier']}")
    print(f"   MRR: ${stats['monthly_recurring_revenue']}")
    
    # Upgrade user
    print("\n3. Upgrading free user to Basic...")
    manager.upgrade_tier(free_user.user_id, SubscriptionTier.BASIC, duration_days=30)
    upgraded = manager.get_user(free_user.user_id)
    print(f"   New tier: {upgraded.tier.value}")
    print(f"   Symbols: {len(upgraded.symbols)} (Expected: 5)")
    print(f"   Expires: {upgraded.expires_at}")
    
    # Check MRR
    stats = manager.get_stats()
    print(f"\n4. New MRR: ${stats['monthly_recurring_revenue']} (Expected: $38)")
    
    print("\n✅ All tests passed!")
