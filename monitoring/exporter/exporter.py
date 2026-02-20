#!/usr/bin/env python3
"""
Crypto Price Exporter for Prometheus
Fetches prices from CoinGecko and exposes as metrics
"""
import time
import requests
from prometheus_client import start_http_server, Gauge, Counter, Info

# Metrics
crypto_price = Gauge('crypto_price_usd', 'Current price in USD', ['symbol', 'name'])
crypto_market_cap = Gauge('crypto_market_cap_usd', 'Market cap in USD', ['symbol', 'name'])
crypto_volume = Gauge('crypto_volume_24h_usd', '24h trading volume in USD', ['symbol', 'name'])
crypto_change_24h = Gauge('crypto_change_24h_percent', '24h price change percentage', ['symbol', 'name'])
crypto_ath = Gauge('crypto_ath_usd', 'All time high in USD', ['symbol', 'name'])
crypto_atl = Gauge('crypto_atl_usd', 'All time low in USD', ['symbol', 'name'])

# Track API calls
api_calls_total = Counter('crypto_api_calls_total', 'Total API calls made', ['status'])

# Exporter info
exporter_info = Info('crypto_exporter', 'Crypto exporter information')

# Coins to track
COINS = ['bitcoin', 'ethereum', 'cardano', 'solana', 'polkadot']

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

def fetch_prices():
    """Fetch prices from CoinGecko"""
    try:
        params = {
            'vs_currency': 'usd',
            'ids': ','.join(COINS),
            'order': 'market_cap_desc',
            'sparkline': 'false'
        }
        response = requests.get(COINGECKO_URL, params=params, timeout=30)
        response.raise_for_status()
        api_calls_total.labels(status='success').inc()
        return response.json()
    except Exception as e:
        print(f"Error fetching prices: {e}")
        api_calls_total.labels(status='error').inc()
        return []

def update_metrics(data):
    """Update Prometheus metrics with price data"""
    for coin in data:
        symbol = coin.get('symbol', 'unknown').upper()
        name = coin.get('name', 'unknown')
        
        crypto_price.labels(symbol=symbol, name=name).set(coin.get('current_price', 0))
        crypto_market_cap.labels(symbol=symbol, name=name).set(coin.get('market_cap', 0))
        crypto_volume.labels(symbol=symbol, name=name).set(coin.get('total_volume', 0))
        crypto_change_24h.labels(symbol=symbol, name=name).set(coin.get('price_change_percentage_24h', 0) or 0)
        crypto_ath.labels(symbol=symbol, name=name).set(coin.get('ath', 0))
        crypto_atl.labels(symbol=symbol, name=name).set(coin.get('atl', 0))
        
        print(f"Updated {symbol}: ${coin.get('current_price', 0)}")

def main():
    # Set exporter info
    exporter_info.info({'version': '1.0.0', 'coins': ','.join(COINS)})
    
    # Start HTTP server on port 8001
    start_http_server(8001)
    print(f"Crypto exporter started on port 8001")
    print(f"Tracking coins: {', '.join(COINS)}")
    
    while True:
        data = fetch_prices()
        if data:
            update_metrics(data)
        time.sleep(60)  # Update every minute

if __name__ == '__main__':
    main()
