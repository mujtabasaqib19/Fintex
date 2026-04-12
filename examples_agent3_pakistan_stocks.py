"""
Example usage for Agent 3: Real-Time Market Agent (Pakistan Stocks)

This file demonstrates how to use the Pakistan Stock Retriever agent
to fetch and analyze Pakistani stock market data from the database.
"""
import sys
import os
from datetime import datetime, timedelta, date

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retrieval import PakistanStockRetriever


def example_get_latest_price():
    """Example: Get latest price for a specific stock."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Get Latest Stock Price")
    print("="*60)
    
    agent = PakistanStockRetriever()
    
    # Get latest price for AKBLTFC6
    symbol = "AKBLTFC6"
    latest = agent.get_latest_price(symbol)
    
    if latest:
        print(f"\n📊 Latest Price for {symbol}:")
        print(agent.format_price_for_context(latest))
    else:
        print(f"\n❌ No data found for {symbol}")


def example_get_price_history():
    """Example: Get historical price data."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Get Price History")
    print("="*60)
    
    agent = PakistanStockRetriever()
    
    symbol = "AKBLTFC6"
    # Get last 7 days of data
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    history = agent.get_price_history(symbol, start_date, end_date, limit=10)
    
    if history:
        print(f"\n📈 Price History for {symbol}:")
        print(agent.format_history_for_context(history, symbol))
    else:
        print(f"\n❌ No historical data found for {symbol}")


def example_get_statistics():
    """Example: Get price statistics and analysis."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Get Price Statistics")
    print("="*60)
    
    agent = PakistanStockRetriever()
    
    symbol = "AKBLTFC6"
    stats = agent.get_price_stats(symbol, days=30)
    
    if stats:
        print(f"\n📊 Statistics for {symbol}:")
        print(agent.format_stats_for_context(stats))
    else:
        print(f"\n❌ No statistics available for {symbol}")


def example_compare_stocks():
    """Example: Compare multiple stocks."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Compare Multiple Stocks")
    print("="*60)
    
    agent = PakistanStockRetriever()
    
    # Get some available symbols
    symbols = agent.get_available_symbols(limit=5)
    
    if symbols:
        print(f"\n🔍 Comparing {len(symbols)} stocks:")
        comparisons = agent.compare_stocks(symbols, days=7)
        
        if comparisons:
            print(agent.format_comparison_for_context(comparisons))
        else:
            print("❌ No comparison data available")
    else:
        print("❌ No symbols available")


def example_market_snapshot():
    """Example: Get market snapshot."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Market Snapshot")
    print("="*60)
    
    agent = PakistanStockRetriever()
    
    snapshot = agent.get_market_snapshot(limit=5)
    
    if snapshot:
        print(f"\n📸 Market Snapshot ({len(snapshot)} stocks):")
        for i, stock in enumerate(snapshot, 1):
            symbol = stock.get('symbol', 'Unknown')
            close = stock.get('close', 0)
            date_str = stock.get('date', 'Unknown')
            volume = stock.get('volume', 0)
            print(f"\n{i}. {symbol}")
            print(f"   Date: {date_str}")
            print(f"   Close: PKR {close:.2f}")
            print(f"   Volume: {volume:,} shares")
    else:
        print("❌ No market data available")


def example_top_movers():
    """Example: Get top gainers and losers."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Top Movers (Gainers)")
    print("="*60)
    
    agent = PakistanStockRetriever()
    
    # Get top gainers
    gainers = agent.get_top_movers(limit=5, days=7, direction='up')
    
    if gainers:
        print(f"\n🚀 Top 5 Gainers (Last 7 Days):")
        for i, stock in enumerate(gainers, 1):
            symbol = stock.get('symbol', 'Unknown')
            change_pct = stock.get('change_percent', 0)
            close = stock.get('latest_close', 0)
            print(f"{i}. {symbol}: PKR {close:.2f} ({change_pct:+.2f}%)")
    else:
        print("❌ No gainer data available")
    
    print("\n" + "="*60)
    print("Top Movers (Losers)")
    print("="*60)
    
    # Get top losers
    losers = agent.get_top_movers(limit=5, days=7, direction='down')
    
    if losers:
        print(f"\n📉 Top 5 Losers (Last 7 Days):")
        for i, stock in enumerate(losers, 1):
            symbol = stock.get('symbol', 'Unknown')
            change_pct = stock.get('change_percent', 0)
            close = stock.get('latest_close', 0)
            print(f"{i}. {symbol}: PKR {close:.2f} ({change_pct:+.2f}%)")
    else:
        print("❌ No loser data available")


def example_volume_analysis():
    """Example: Analyze trading volume."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Volume Analysis")
    print("="*60)
    
    agent = PakistanStockRetriever()
    
    symbol = "AKBLTFC6"
    volume_stats = agent.get_volume_analysis(symbol, days=30)
    
    if volume_stats:
        print(f"\n📊 Volume Analysis for {symbol}:")
        print(f"Period: {volume_stats.get('period_days', 0)} days")
        print(f"Total Volume: {volume_stats.get('total_volume', 0):,} shares")
        print(f"Avg Daily Volume: {volume_stats.get('avg_daily_volume', 0):,.0f} shares")
        print(f"Max Volume: {volume_stats.get('max_volume', 0):,} shares")
        print(f"Min Volume: {volume_stats.get('min_volume', 0):,} shares")
        print(f"Latest Volume: {volume_stats.get('latest_volume', 0):,} shares")
    else:
        print(f"❌ No volume data available for {symbol}")


def example_llm_integration():
    """Example: Format data for LLM context (Q&A integration)."""
    print("\n" + "="*60)
    print("EXAMPLE 8: LLM Integration (Formatted Context)")
    print("="*60)
    
    agent = PakistanStockRetriever()
    
    # Simulate a query: "What's the latest price of AKBLTFC6?"
    symbol = "AKBLTFC6"
    latest = agent.get_latest_price(symbol)
    
    if latest:
        # Format for LLM
        context = agent.format_price_for_context(latest)
        
        print(f"\n🤖 Context for LLM Query:")
        print(f"User Query: 'What is the latest price of {symbol}?'")
        print(f"\nRetrieved Context:")
        print("---")
        print(context)
        print("---")
        print("\nThis context can be fed to an LLM to generate a natural language answer.")
    else:
        print(f"❌ No data found for {symbol}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("AGENT 3: PAKISTAN STOCK MARKET RETRIEVER - EXAMPLES")
    print("Real-Time Market Agent for Pakistan Stocks")
    print("="*60)
    
    try:
        # Check available symbols first
        agent = PakistanStockRetriever()
        symbols = agent.get_available_symbols(limit=5)
        
        print(f"\n✅ Connected to database")
        print(f"📊 Available symbols (sample): {', '.join(symbols[:5]) if symbols else 'None'}")
        
        # Run examples
        example_get_latest_price()
        example_get_price_history()
        example_get_statistics()
        example_compare_stocks()
        example_market_snapshot()
        example_top_movers()
        example_volume_analysis()
        example_llm_integration()
        
        print("\n" + "="*60)
        print("ALL EXAMPLES COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("\nMake sure:")
        print("  1. Database connection is configured in .env")
        print("  2. stock_prices table exists in Supabase")
        print("  3. Data has been ingested into the table")


if __name__ == "__main__":
    main()
