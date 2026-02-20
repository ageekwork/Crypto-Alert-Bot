#!/usr/bin/env python3
"""
Crypto Alert Bot - Whale Tracker
Monitors large wallet movements and exchange inflows/outflows
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class WhaleAlert:
    """Represents a whale movement alert"""
    blockchain: str
    symbol: str
    amount: float
    amount_usd: float
    from_address: str
    to_address: str
    from_owner: Optional[str]
    to_owner: Optional[str]
    transaction_type: str  # 'transfer', 'exchange_in', 'exchange_out', 'unknown'
    timestamp: str
    tx_hash: str


class WhaleTracker:
    """
    Tracks large cryptocurrency movements (whale watching)
    Uses free APIs (Whale Alert API, Blockchain explorers)
    """
    
    def __init__(self, min_usd_value: float = 100000):
        """
        Args:
            min_usd_value: Minimum USD value to consider a "whale" transaction
        """
        self.min_usd_value = min_usd_value
        self.session = requests.Session()
        
        # Known exchange addresses (simplified)
        self.exchange_addresses = {
            'binance': ['binance', 'bnb', 'binance.com'],
            'coinbase': ['coinbase', 'coinbase.com', 'cb'],
            'kraken': ['kraken', 'kraken.com'],
            'okx': ['okx', 'okex'],
            'bybit': ['bybit'],
            'kucoin': ['kucoin', 'kucoin.com'],
        }
    
    def get_bitcoin_whale_transactions(self, hours: int = 1) -> List[WhaleAlert]:
        """
        Get large Bitcoin transactions
        Uses Blockchain.com API (free, limited)
        """
        alerts = []
        
        try:
            # Get latest block
            url = "https://blockchain.info/latestblock"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                latest = response.json()
                latest_height = latest['height']
                
                # Get blocks from last hour (~6 blocks)
                blocks_to_check = min(6, hours * 6)
                
                for i in range(blocks_to_check):
                    block_height = latest_height - i
                    block_url = f"https://blockchain.info/rawblock/{block_height}"
                    
                    block_response = self.session.get(block_url, timeout=10)
                    if block_response.status_code == 200:
                        block_data = block_response.json()
                        
                        # Check each transaction
                        for tx in block_data.get('tx', [])[:50]:  # Limit to first 50
                            # Calculate total output value
                            total_output = sum(out.get('value', 0) for out in tx.get('out', []))
                            total_btc = total_output / 100000000  # Convert satoshis to BTC
                            
                            # Rough USD estimate (would use real price in production)
                            btc_price = 70000  # Approximate
                            usd_value = total_btc * btc_price
                            
                            if usd_value >= self.min_usd_value:
                                # Determine transaction type
                                tx_type = self._classify_transaction(tx, 'bitcoin')
                                
                                alert = WhaleAlert(
                                    blockchain='bitcoin',
                                    symbol='BTC',
                                    amount=total_btc,
                                    amount_usd=usd_value,
                                    from_address=tx.get('inputs', [{}])[0].get('prev_out', {}).get('addr', 'unknown') if tx.get('inputs') else 'unknown',
                                    to_address=tx.get('out', [{}])[0].get('addr', 'unknown') if tx.get('out') else 'unknown',
                                    from_owner=None,
                                    to_owner=None,
                                    transaction_type=tx_type,
                                    timestamp=datetime.fromtimestamp(block_data['time']).isoformat(),
                                    tx_hash=tx.get('hash', '')
                                )
                                alerts.append(alert)
        
        except Exception as e:
            print(f"Error fetching Bitcoin data: {e}")
        
        return sorted(alerts, key=lambda x: x.amount_usd, reverse=True)[:20]
    
    def get_ethereum_whale_transactions(self, hours: int = 1) -> List[WhaleAlert]:
        """
        Get large Ethereum transactions
        Uses Etherscan API (free tier available)
        """
        alerts = []
        
        # Note: Requires API key for production use
        # This is a placeholder implementation
        
        try:
            # Using Etherscan API (would need API key)
            # For now, return empty list as example
            pass
        
        except Exception as e:
            print(f"Error fetching Ethereum data: {e}")
        
        return alerts
    
    def _classify_transaction(self, tx: Dict, blockchain: str) -> str:
        """
        Classify transaction type based on addresses
        """
        addresses = []
        
        # Collect all addresses from inputs and outputs
        if blockchain == 'bitcoin':
            for inp in tx.get('inputs', []):
                addr = inp.get('prev_out', {}).get('addr', '')
                if addr:
                    addresses.append(addr.lower())
            
            for out in tx.get('out', []):
                addr = out.get('addr', '')
                if addr:
                    addresses.append(addr.lower())
        
        # Check if any address belongs to known exchanges
        has_exchange = False
        for addr in addresses:
            for exchange, keywords in self.exchange_addresses.items():
                if any(kw in addr for kw in keywords):
                    has_exchange = True
                    break
        
        # Simple classification
        if has_exchange:
            return 'exchange_related'
        
        return 'transfer'
    
    def get_exchange_inflows(self, exchange: str = 'binance', hours: int = 1) -> Dict:
        """
        Get estimated exchange inflows
        Uses Glassnode or similar (would need API key for production)
        """
        # Placeholder - would require paid API
        return {
            'exchange': exchange,
            'period_hours': hours,
            'total_btc_inflow': 0,
            'total_btc_outflow': 0,
            'net_flow': 0,
            'note': 'Requires Glassnode/CryptoQuant API key for real data'
        }
    
    def format_alert(self, alert: WhaleAlert) -> str:
        """Format a whale alert for display/notification"""
        emoji = '🐋' if alert.amount_usd > 10000000 else '🐳' if alert.amount_usd > 1000000 else '🐟'
        
        msg = f"""
{emoji} **WHALE ALERT** {emoji}

**{alert.amount:,.2f} {alert.symbol}** (${alert.amount_usd:,.0f})

Blockchain: {alert.blockchain.upper()}
Type: {alert.transaction_type.replace('_', ' ').title()}
Time: {alert.timestamp}

From: `{alert.from_address[:20]}...`
To: `{alert.to_address[:20]}...`

[View Transaction](https://www.blockchain.com/explorer/transactions/btc/{alert.tx_hash})
"""
        return msg


class WhaleAlertMock:
    """
    Mock whale tracker for testing without API keys
    Generates sample alerts for demonstration
    """
    
    def __init__(self, min_usd_value: float = 100000):
        self.min_usd_value = min_usd_value
    
    def get_bitcoin_whale_transactions(self, hours: int = 1) -> List[WhaleAlert]:
        """Generate sample whale alerts"""
        import random
        
        sample_alerts = [
            WhaleAlert(
                blockchain='bitcoin',
                symbol='BTC',
                amount=1500.5,
                amount_usd=105035000,
                from_address='1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
                to_address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                from_owner='Unknown Wallet',
                to_owner='Binance',
                transaction_type='exchange_in',
                timestamp=datetime.now().isoformat(),
                tx_hash='abc123def456'
            ),
            WhaleAlert(
                blockchain='bitcoin',
                symbol='BTC',
                amount=750.25,
                amount_usd=52517500,
                from_address='bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h',
                to_address='1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
                from_owner='Coinbase',
                to_owner='Unknown Wallet',
                transaction_type='exchange_out',
                timestamp=(datetime.now() - timedelta(minutes=15)).isoformat(),
                tx_hash='def789ghi012'
            ),
            WhaleAlert(
                blockchain='bitcoin',
                symbol='BTC',
                amount=3000.0,
                amount_usd=210000000,
                from_address='1BoatSLRHtKNngkdXEeobR76b53LETtpyT',
                to_address='bc1q2gjc0l80zxd6z0w8s90j9y9h6r8z7w',
                from_owner=None,
                to_owner=None,
                transaction_type='transfer',
                timestamp=(datetime.now() - timedelta(minutes=30)).isoformat(),
                tx_hash='ghi345jkl678'
            ),
        ]
        
        return [a for a in sample_alerts if a.amount_usd >= self.min_usd_value]


if __name__ == '__main__':
    print("Testing Whale Tracker")
    print("=" * 60)
    
    # Use mock for testing
    tracker = WhaleAlertMock(min_usd_value=100000)
    
    alerts = tracker.get_bitcoin_whale_transactions(hours=1)
    
    print(f"\n🐋 Found {len(alerts)} whale transactions\n")
    
    for alert in alerts:
        print(tracker.format_alert(alert))
        print("-" * 60)
