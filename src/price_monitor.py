#!/usr/bin/env python3
"""
Crypto Alert Bot - Multi-Exchange Price Monitor
Monitors prices across exchanges and detects opportunities
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict
import threading


@dataclass
class PriceData:
    """Represents price data from an exchange"""
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume_24h: Optional[float] = None
    change_24h: Optional[float] = None
    timestamp: str = None
    exchange: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass  
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity between exchanges"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    profit_pct: float
    profit_usd: float
    timestamp: str


class PriceMonitor:
    """
    Monitors cryptocurrency prices across multiple exchanges
    """
    
    def __init__(self, poll_interval: int = 10):
        """
        Args:
            poll_interval: Seconds between price updates
        """
        self.poll_interval = poll_interval
        self.prices: Dict[str, Dict[str, PriceData]] = defaultdict(dict)
        self.callbacks: List[Callable] = []
        self.running = False
        self.thread = None
        
        # Exchange configurations
        self.exchanges = {
            'binance': self._fetch_binance,
            'coinbase': self._fetch_coinbase,
            'kraken': self._fetch_kraken,
            'bybit': self._fetch_bybit,
            'kucoin': self._fetch_kucoin,
        }
    
    def add_callback(self, callback: Callable):
        """Add a callback function to be called on price updates"""
        self.callbacks.append(callback)
    
    def _fetch_binance(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Fetch prices from Binance"""
        results = {}
        try:
            # Convert symbols to Binance format (BTCUSDT)
            binance_symbols = [s.replace('/', '').upper() for s in symbols]
            symbol_str = json.dumps(binance_symbols)
            
            url = "https://api.binance.com/api/v3/ticker/24hr"
            response = requests.get(url, params={'symbols': symbol_str}, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    symbol = f"{item['symbol'][:-4]}/{item['symbol'][-4:]}"  # BTCUSDT -> BTC/USDT
                    results[symbol] = PriceData(
                        symbol=symbol,
                        price=float(item['lastPrice']),
                        bid=float(item.get('bidPrice', 0)),
                        ask=float(item.get('askPrice', 0)),
                        volume_24h=float(item['volume']),
                        change_24h=float(item['priceChangePercent']),
                        exchange='binance'
                    )
        except Exception as e:
            print(f"Error fetching Binance: {e}")
        
        return results
    
    def _fetch_coinbase(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Fetch prices from Coinbase"""
        results = {}
        try:
            for symbol in symbols:
                # Convert to Coinbase format (BTC-USD)
                cb_symbol = symbol.replace('/', '-')
                url = f"https://api.exchange.coinbase.com/products/{cb_symbol}/ticker"
                
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    results[symbol] = PriceData(
                        symbol=symbol,
                        price=float(data['price']),
                        bid=float(data.get('bid', 0)),
                        ask=float(data.get('ask', 0)),
                        volume_24h=float(data.get('volume', 0)),
                        exchange='coinbase'
                    )
                time.sleep(0.1)  # Rate limiting
        except Exception as e:
            print(f"Error fetching Coinbase: {e}")
        
        return results
    
    def _fetch_kraken(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Fetch prices from Kraken"""
        results = {}
        try:
            # Kraken uses different symbol format
            symbol_map = {s: s.replace('/', '') for s in symbols}
            symbol_str = ','.join(symbol_map.values())
            
            url = "https://api.kraken.com/0/public/Ticker"
            response = requests.get(url, params={'pair': symbol_str}, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    for original, kraken_sym in symbol_map.items():
                        if kraken_sym in data['result']:
                            ticker = data['result'][kraken_sym]
                            results[original] = PriceData(
                                symbol=original,
                                price=float(ticker['c'][0]),
                                bid=float(ticker['b'][0]),
                                ask=float(ticker['a'][0]),
                                volume_24h=float(ticker['v'][1]),
                                exchange='kraken'
                            )
        except Exception as e:
            print(f"Error fetching Kraken: {e}")
        
        return results
    
    def _fetch_bybit(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Fetch prices from Bybit"""
        results = {}
        try:
            for symbol in symbols:
                bb_symbol = symbol.replace('/', '')
                url = "https://api.bybit.com/v5/market/tickers"
                
                response = requests.get(url, params={'category': 'spot', 'symbol': bb_symbol}, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('retCode') == 0 and 'result' in data:
                        ticker = data['result']['list'][0]
                        results[symbol] = PriceData(
                            symbol=symbol,
                            price=float(ticker['lastPrice']),
                            bid=float(ticker.get('bid1Price', 0)),
                            ask=float(ticker.get('ask1Price', 0)),
                            volume_24h=float(ticker.get('volume24h', 0)),
                            change_24h=float(ticker.get('price24hPcnt', 0)) * 100,
                            exchange='bybit'
                        )
                time.sleep(0.1)
        except Exception as e:
            print(f"Error fetching Bybit: {e}")
        
        return results
    
    def _fetch_kucoin(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Fetch prices from KuCoin"""
        results = {}
        try:
            url = "https://api.kucoin.com/api/v1/market/allTickers"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and 'ticker' in data['data']:
                    for ticker in data['data']['ticker']:
                        symbol = ticker['symbol']
                        # Convert to standard format
                        if '-USDT' in symbol or 'USDT' in symbol:
                            base = symbol.replace('USDT', '').replace('-', '')
                            std_symbol = f"{base}/USDT"
                            
                            if std_symbol in symbols:
                                results[std_symbol] = PriceData(
                                    symbol=std_symbol,
                                    price=float(ticker['last']),
                                    bid=float(ticker.get('buy', 0)),
                                    ask=float(ticker.get('sell', 0)),
                                    volume_24h=float(ticker.get('volValue', 0)),
                                    change_24h=float(ticker.get('changeRate', 0)) * 100,
                                    exchange='kucoin'
                                )
        except Exception as e:
            print(f"Error fetching KuCoin: {e}")
        
        return results
    
    def fetch_all_prices(self, symbols: List[str]) -> Dict[str, Dict[str, PriceData]]:
        """
        Fetch prices from all exchanges for given symbols
        
        Returns:
            {symbol: {exchange: PriceData}}
        """
        all_prices = defaultdict(dict)
        
        for exchange_name, fetch_func in self.exchanges.items():
            try:
                prices = fetch_func(symbols)
                for symbol, price_data in prices.items():
                    all_prices[symbol][exchange_name] = price_data
                    self.prices[symbol][exchange_name] = price_data
            except Exception as e:
                print(f"Error with {exchange_name}: {e}")
        
        return all_prices
    
    def find_arbitrage(self, symbols: List[str], min_profit_pct: float = 0.5) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities across exchanges
        
        Args:
            symbols: List of trading pairs to check
            min_profit_pct: Minimum profit percentage to report
        
        Returns:
            List of ArbitrageOpportunity objects
        """
        opportunities = []
        
        for symbol in symbols:
            if symbol not in self.prices:
                continue
            
            exchange_prices = self.prices[symbol]
            if len(exchange_prices) < 2:
                continue
            
            # Find best bid (highest buy price) and best ask (lowest sell price)
            bids = [(ex, pd.bid) for ex, pd in exchange_prices.items() if pd.bid]
            asks = [(ex, pd.ask) for ex, pd in exchange_prices.items() if pd.ask]
            
            if not bids or not asks:
                continue
            
            best_bid = max(bids, key=lambda x: x[1])  # Highest price someone will pay
            best_ask = min(asks, key=lambda x: x[1])  # Lowest price you can buy at
            
            buy_exchange, buy_price = best_ask
            sell_exchange, sell_price = best_bid
            
            # Calculate profit
            if sell_price > buy_price:
                profit_pct = ((sell_price - buy_price) / buy_price) * 100
                profit_usd = sell_price - buy_price
                
                if profit_pct >= min_profit_pct:
                    opp = ArbitrageOpportunity(
                        symbol=symbol,
                        buy_exchange=buy_exchange,
                        sell_exchange=sell_exchange,
                        buy_price=buy_price,
                        sell_price=sell_price,
                        profit_pct=profit_pct,
                        profit_usd=profit_usd,
                        timestamp=datetime.now().isoformat()
                    )
                    opportunities.append(opp)
        
        return sorted(opportunities, key=lambda x: x.profit_pct, reverse=True)
    
    def start_monitoring(self, symbols: List[str]):
        """Start continuous monitoring in background thread"""
        self.running = True
        
        def monitor_loop():
            while self.running:
                try:
                    prices = self.fetch_all_prices(symbols)
                    
                    # Call all callbacks
                    for callback in self.callbacks:
                        try:
                            callback(prices)
                        except Exception as e:
                            print(f"Callback error: {e}")
                    
                except Exception as e:
                    print(f"Monitoring error: {e}")
                
                time.sleep(self.poll_interval)
        
        self.thread = threading.Thread(target=monitor_loop, daemon=True)
        self.thread.start()
        print(f"✅ Price monitoring started for {len(symbols)} symbols")
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("⏹️  Price monitoring stopped")


if __name__ == '__main__':
    # Test the monitor
    monitor = PriceMonitor(poll_interval=10)
    
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    
    print("Testing Price Monitor")
    print("=" * 60)
    
    # Fetch once
    prices = monitor.fetch_all_prices(symbols)
    
    print(f"\nPrices fetched:")
    for symbol, exchange_data in prices.items():
        print(f"\n{symbol}:")
        for exchange, data in exchange_data.items():
            print(f"  {exchange:10}: ${data.price:,.2f}")
    
    # Find arbitrage
    print("\n" + "=" * 60)
    print("Looking for arbitrage opportunities...")
    opps = monitor.find_arbitrage(symbols, min_profit_pct=0.1)
    
    if opps:
        print(f"\n🎯 Found {len(opps)} opportunities:")
        for opp in opps[:5]:
            print(f"\n  {opp.symbol}:")
            print(f"    Buy on {opp.buy_exchange} at ${opp.buy_price:,.2f}")
            print(f"    Sell on {opp.sell_exchange} at ${opp.sell_price:,.2f}")
            print(f"    Profit: {opp.profit_pct:.2f}% (${opp.profit_usd:.2f})")
    else:
        print("\n  No arbitrage opportunities found")
