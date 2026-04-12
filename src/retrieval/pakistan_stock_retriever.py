"""
Agent 3: Real-Time Market Agent for Pakistan Stocks

This agent retrieves live stock prices, market movements, and trading data
specifically for Pakistan Stock Exchange (PSX) stocks from the stock_prices table.

🤖 Agent 3: Real-Time Market Agent Retrieves:
- Live stock prices
- Market movements
- Trading data
- Historical price data for Pakistani stocks

Database: Supabase - stock_prices table
Context: Pakistan Finance Expert (not global)
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, date
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.categories import SectorCategory
from src.db.connection import get_supabase_client
from config.settings import get_settings


class PakistanStockRetriever:
    """
    Agent 3: Real-Time Market Agent for Pakistan Stocks
    
    Specialized retriever for Pakistan Stock Exchange (PSX) data.
    Provides methods for:
    - Getting current/latest stock prices
    - Fetching historical price data (OHLC)
    - Computing market statistics
    - Finding related stocks
    - Analyzing trading volumes
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.settings = get_settings()
        self.table_name = "stock_prices"
    
    # =========================================================================
    # STOCK LOOKUP & VALIDATION
    # =========================================================================
    
    def get_available_symbols(self, limit: int = 100) -> List[str]:
        """
        Get list of all available stock symbols in the database.
        
        Args:
            limit: Maximum number of symbols to return
            
        Returns:
            List of unique stock symbols
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select("symbol")\
                .order("symbol")\
                .limit(limit)\
                .execute()
            
            if result.data:
                # Get unique symbols
                symbols = list(set([row['symbol'] for row in result.data]))
                return sorted(symbols)
            return []
        except Exception as e:
            print(f"Error fetching symbols: {e}")
            return []
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Check if a symbol exists in the database.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            True if symbol exists, False otherwise
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select("symbol")\
                .eq("symbol", symbol.upper())\
                .limit(1)\
                .execute()
            
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            print(f"Error validating symbol: {e}")
            return False
    
    # =========================================================================
    # LATEST/CURRENT PRICE DATA
    # =========================================================================
    
    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent price data for a stock.
        
        Args:
            symbol: Stock symbol (e.g., 'AKBLTFC6')
            
        Returns:
            Latest price record with OHLC data or None
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("symbol", symbol.upper())\
                .order("date", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error fetching latest price for {symbol}: {e}")
            return None
    
    def get_multiple_latest_prices(
        self, 
        symbols: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get latest prices for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dict mapping symbol to latest price data
        """
        results = {}
        for symbol in symbols:
            latest = self.get_latest_price(symbol)
            if latest:
                results[symbol] = latest
        return results
    
    def get_market_snapshot(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get latest prices for top stocks (market snapshot).
        
        Args:
            limit: Number of stocks to include
            
        Returns:
            List of latest price records for top stocks
        """
        try:
            # Get unique symbols first
            symbols = self.get_available_symbols(limit=limit)
            
            # Get latest price for each
            snapshot = []
            for symbol in symbols[:limit]:
                latest = self.get_latest_price(symbol)
                if latest:
                    snapshot.append(latest)
            
            return snapshot
        except Exception as e:
            print(f"Error fetching market snapshot: {e}")
            return []
    
    # =========================================================================
    # HISTORICAL PRICE DATA
    # =========================================================================
    
    def get_price_history(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data for a stock.
        
        Args:
            symbol: Stock symbol
            start_date: Start date (defaults to 30 days ago)
            end_date: End date (defaults to today)
            limit: Maximum number of records
            
        Returns:
            List of price records ordered by date
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        try:
            query = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("symbol", symbol.upper())\
                .gte("date", start_date.isoformat())\
                .lte("date", end_date.isoformat())\
                .order("date", desc=False)\
                .limit(limit)
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            print(f"Error fetching price history for {symbol}: {e}")
            return []
    
    def get_specific_date_price(
        self,
        symbol: str,
        target_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Get price data for a specific date.
        
        Args:
            symbol: Stock symbol
            target_date: Target date
            
        Returns:
            Price record for the specified date or None
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("symbol", symbol.upper())\
                .eq("date", target_date.isoformat())\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error fetching price for {symbol} on {target_date}: {e}")
            return None
    
    # =========================================================================
    # STATISTICS & ANALYSIS
    # =========================================================================
    
    def get_price_stats(
        self,
        symbol: str,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate statistical metrics for a stock over a period.
        
        Args:
            symbol: Stock symbol
            days: Number of days to analyze
            
        Returns:
            Stats dict with min, max, avg, volatility, etc.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        data = self.get_price_history(symbol, start_date, end_date, limit=days)
        
        if not data or len(data) == 0:
            return None
        
        # Extract values
        close_prices = [float(d.get('close', 0)) for d in data if d.get('close')]
        volumes = [int(d.get('volume', 0)) for d in data if d.get('volume')]
        highs = [float(d.get('high', 0)) for d in data if d.get('high')]
        lows = [float(d.get('low', 0)) for d in data if d.get('low')]
        
        if not close_prices:
            return None
        
        # Calculate statistics
        latest_close = close_prices[-1] if close_prices else 0
        first_close = close_prices[0] if close_prices else 0
        
        stats = {
            'symbol': symbol,
            'period_days': days,
            'data_points': len(data),
            'latest_close': latest_close,
            'latest_date': data[-1].get('date') if data else None,
            'min_close': min(close_prices) if close_prices else 0,
            'max_close': max(close_prices) if close_prices else 0,
            'avg_close': sum(close_prices) / len(close_prices) if close_prices else 0,
            'total_volume': sum(volumes) if volumes else 0,
            'avg_volume': sum(volumes) / len(volumes) if volumes else 0,
            'highest_high': max(highs) if highs else 0,
            'lowest_low': min(lows) if lows else 0,
        }
        
        # Calculate change
        if first_close > 0:
            change = latest_close - first_close
            change_pct = (change / first_close) * 100
            stats['change'] = round(change, 2)
            stats['change_percent'] = round(change_pct, 2)
            stats['trend'] = 'up' if change_pct > 0 else 'down' if change_pct < 0 else 'stable'
        else:
            stats['change'] = 0
            stats['change_percent'] = 0
            stats['trend'] = 'stable'
        
        return stats
    
    def get_volume_analysis(
        self,
        symbol: str,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze trading volume patterns for a stock.
        
        Args:
            symbol: Stock symbol
            days: Number of days to analyze
            
        Returns:
            Volume analysis dict
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        data = self.get_price_history(symbol, start_date, end_date, limit=days)
        
        if not data or len(data) == 0:
            return None
        
        volumes = [int(d.get('volume', 0)) for d in data]
        
        if not volumes:
            return None
        
        return {
            'symbol': symbol,
            'period_days': days,
            'total_volume': sum(volumes),
            'avg_daily_volume': sum(volumes) / len(volumes),
            'max_volume': max(volumes),
            'min_volume': min(volumes),
            'latest_volume': volumes[-1] if volumes else 0,
            'days_analyzed': len(volumes)
        }
    
    # =========================================================================
    # COMPARISON & RANKING
    # =========================================================================
    
    def compare_stocks(
        self,
        symbols: List[str],
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Compare performance of multiple stocks.
        
        Args:
            symbols: List of stock symbols to compare
            days: Number of days for comparison
            
        Returns:
            List of comparison stats for each stock
        """
        comparisons = []
        
        for symbol in symbols:
            stats = self.get_price_stats(symbol, days)
            if stats:
                comparisons.append(stats)
        
        # Sort by change percentage (descending)
        comparisons.sort(key=lambda x: x.get('change_percent', 0), reverse=True)
        
        return comparisons
    
    def get_top_movers(
        self,
        limit: int = 10,
        days: int = 7,
        direction: str = 'up'
    ) -> List[Dict[str, Any]]:
        """
        Get top gaining or losing stocks.
        
        Args:
            limit: Number of stocks to return
            days: Period for calculating change
            direction: 'up' for gainers, 'down' for losers
            
        Returns:
            List of top movers with their stats
        """
        symbols = self.get_available_symbols(limit=100)
        
        all_stats = []
        for symbol in symbols:
            stats = self.get_price_stats(symbol, days)
            if stats and stats.get('change_percent') is not None:
                all_stats.append(stats)
        
        # Sort based on direction
        if direction.lower() == 'up':
            all_stats.sort(key=lambda x: x.get('change_percent', 0), reverse=True)
        else:
            all_stats.sort(key=lambda x: x.get('change_percent', 0))
        
        return all_stats[:limit]
    
    # =========================================================================
    # FORMATTING FOR CONTEXT (LLM Integration)
    # =========================================================================
    
    def format_price_for_context(
        self,
        price_data: Dict[str, Any]
    ) -> str:
        """
        Format stock price data for LLM context.
        
        Args:
            price_data: Stock price record
            
        Returns:
            Formatted string for LLM consumption
        """
        if not price_data:
            return "No price data available."
        
        symbol = price_data.get('symbol', 'Unknown')
        date_str = price_data.get('date', 'Unknown')
        open_price = price_data.get('open', 0)
        high = price_data.get('high', 0)
        low = price_data.get('low', 0)
        close = price_data.get('close', 0)
        volume = price_data.get('volume', 0)
        
        lines = [
            f"Stock: {symbol}",
            f"Date: {date_str}",
            f"Open: PKR {open_price:.2f}",
            f"High: PKR {high:.2f}",
            f"Low: PKR {low:.2f}",
            f"Close: PKR {close:.2f}",
            f"Volume: {volume:,} shares"
        ]
        
        return "\n".join(lines)
    
    def format_history_for_context(
        self,
        history: List[Dict[str, Any]],
        symbol: str
    ) -> str:
        """
        Format historical price data for LLM context.
        
        Args:
            history: List of price records
            symbol: Stock symbol
            
        Returns:
            Formatted string showing price history
        """
        if not history:
            return f"No historical data available for {symbol}."
        
        lines = [
            f"Price History for {symbol}",
            f"Period: {history[0].get('date')} to {history[-1].get('date')}",
            f"Records: {len(history)}",
            "---"
        ]
        
        # Show summary
        close_prices = [float(d.get('close', 0)) for d in history if d.get('close')]
        if close_prices:
            lines.append(f"Latest Close: PKR {close_prices[-1]:.2f}")
            lines.append(f"Min Close: PKR {min(close_prices):.2f}")
            lines.append(f"Max Close: PKR {max(close_prices):.2f}")
            lines.append(f"Avg Close: PKR {sum(close_prices)/len(close_prices):.2f}")
            
            # Change calculation
            if len(close_prices) >= 2:
                change = close_prices[-1] - close_prices[0]
                change_pct = (change / close_prices[0] * 100) if close_prices[0] > 0 else 0
                lines.append(f"Change: PKR {change:.2f} ({change_pct:+.2f}%)")
        
        # Show recent data points (last 10)
        lines.append("---")
        lines.append("Recent Prices:")
        for record in history[-10:]:
            date_str = record.get('date', '')
            close = record.get('close', 0)
            volume = record.get('volume', 0)
            lines.append(f"  {date_str}: PKR {close:.2f} (Vol: {volume:,})")
        
        return "\n".join(lines)
    
    def format_stats_for_context(
        self,
        stats: Dict[str, Any]
    ) -> str:
        """
        Format statistical analysis for LLM context.
        
        Args:
            stats: Stats dictionary
            
        Returns:
            Formatted string with statistics
        """
        if not stats:
            return "No statistics available."
        
        lines = [
            f"Stock Analysis: {stats.get('symbol', 'Unknown')}",
            f"Period: {stats.get('period_days', 0)} days",
            f"Data Points: {stats.get('data_points', 0)}",
            "---",
            f"Latest Close: PKR {stats.get('latest_close', 0):.2f}",
            f"Latest Date: {stats.get('latest_date', 'Unknown')}",
            "---",
            f"Min Close: PKR {stats.get('min_close', 0):.2f}",
            f"Max Close: PKR {stats.get('max_close', 0):.2f}",
            f"Avg Close: PKR {stats.get('avg_close', 0):.2f}",
            "---",
            f"Change: PKR {stats.get('change', 0):.2f} ({stats.get('change_percent', 0):+.2f}%)",
            f"Trend: {stats.get('trend', 'stable').upper()}",
            "---",
            f"Total Volume: {stats.get('total_volume', 0):,} shares",
            f"Avg Daily Volume: {stats.get('avg_volume', 0):,.0f} shares"
        ]
        
        return "\n".join(lines)
    
    def format_comparison_for_context(
        self,
        comparisons: List[Dict[str, Any]]
    ) -> str:
        """
        Format stock comparison for LLM context.
        
        Args:
            comparisons: List of stock stats
            
        Returns:
            Formatted comparison string
        """
        if not comparisons:
            return "No comparison data available."
        
        lines = [
            "Stock Performance Comparison",
            "=" * 60
        ]
        
        for i, stats in enumerate(comparisons, 1):
            symbol = stats.get('symbol', 'Unknown')
            close = stats.get('latest_close', 0)
            change = stats.get('change', 0)
            change_pct = stats.get('change_percent', 0)
            trend = stats.get('trend', 'stable')
            
            lines.append(f"\n{i}. {symbol}")
            lines.append(f"   Latest: PKR {close:.2f}")
            lines.append(f"   Change: PKR {change:.2f} ({change_pct:+.2f}%)")
            lines.append(f"   Trend: {trend.upper()}")
        
        return "\n".join(lines)
