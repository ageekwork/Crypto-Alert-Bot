#!/usr/bin/env python3
"""
Crypto Alert Bot - Tests
Simple tests to verify functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from price_monitor import PriceMonitor
from whale_tracker import WhaleAlertMock
from alert_manager import AlertManager, AlertType


def test_price_monitor():
    """Test price monitoring"""
    print("Testing Price Monitor...")
    
    monitor = PriceMonitor()
    symbols = ['BTC/USDT', 'ETH/USDT']
    
    # Test fetching prices
    prices = monitor.fetch_all_prices(symbols)
    
    assert len(prices) > 0, "No prices fetched"
    
    for symbol, exchange_data in prices.items():
        print(f"  ✓ {symbol}: {len(exchange_data)} exchanges")
        for exchange, data in exchange_data.items():
            assert data.price > 0, f"Invalid price for {symbol} on {exchange}"
    
    print("  ✓ Price monitor test passed\n")
    return True


def test_whale_tracker():
    """Test whale tracking"""
    print("Testing Whale Tracker...")
    
    tracker = WhaleAlertMock(min_usd_value=1000000)
    alerts = tracker.get_bitcoin_whale_transactions(hours=1)
    
    assert len(alerts) > 0, "No whale alerts generated"
    
    for alert in alerts:
        assert alert.amount_usd >= 1000000, "Alert below threshold"
        print(f"  ✓ Whale: {alert.amount:,.2f} BTC (${alert.amount_usd:,.0f})")
    
    print("  ✓ Whale tracker test passed\n")
    return True


def test_alert_manager():
    """Test alert management"""
    print("Testing Alert Manager...")
    
    manager = AlertManager()
    
    # Test sending alerts
    result = manager.send_price_alert(
        symbol='BTC/USDT',
        current_price=70000.0,
        change_pct=5.0,
        threshold_pct=3.0
    )
    
    assert result == True, "Alert not sent"
    
    stats = manager.get_alert_stats()
    assert stats['total_alerts'] > 0, "No alerts in stats"
    
    print(f"  ✓ Alerts sent: {stats['total_alerts']}")
    print("  ✓ Alert manager test passed\n")
    return True


def test_arbitrage_detection():
    """Test arbitrage detection"""
    print("Testing Arbitrage Detection...")
    
    monitor = PriceMonitor()
    symbols = ['BTC/USDT']
    
    # Fetch prices
    monitor.fetch_all_prices(symbols)
    
    # Find opportunities
    opportunities = monitor.find_arbitrage(symbols, min_profit_pct=0.1)
    
    print(f"  Found {len(opportunities)} arbitrage opportunities")
    
    for opp in opportunities[:3]:
        print(f"  ✓ {opp.symbol}: {opp.profit_pct:.2f}% profit")
    
    print("  ✓ Arbitrage detection test passed\n")
    return True


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("Crypto Alert Bot - Test Suite")
    print("="*60 + "\n")
    
    tests = [
        test_price_monitor,
        test_whale_tracker,
        test_alert_manager,
        test_arbitrage_detection,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ Test failed: {e}\n")
            failed += 1
    
    print("="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
