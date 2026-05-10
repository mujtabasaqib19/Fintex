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

    def get_fundamentals(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get annual fundamental data for a stock.
        """
        try:
            result = self.supabase.table("company_fundamentals")\
                .select("*")\
                .eq("symbol", symbol.upper())\
                .order("fiscal_year", desc=True)\
                .execute()
            
            return result.data or []
        except Exception as e:
            print(f"Error fetching fundamentals for {symbol}: {e}")
            return []
    
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
    # TECHNICAL ANALYSIS FOR PREDICTIONS
    # =========================================================================

    def _compute_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Relative Strength Index over the last `period` closes."""
        if len(prices) < period + 1:
            return None
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0.0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0.0 for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _compute_ema(self, prices: List[float], period: int) -> List[float]:
        """Exponential Moving Average; seeds with SMA of first `period` values."""
        if len(prices) < period:
            return []
        k = 2.0 / (period + 1)
        ema = [sum(prices[:period]) / period]
        for price in prices[period:]:
            ema.append(price * k + ema[-1] * (1 - k))
        return ema

    def _compute_macd(self, prices: List[float]) -> Optional[Dict[str, Any]]:
        """MACD (12,26,9). Requires at least 34 data points."""
        if len(prices) < 34:
            return None
        ema12 = self._compute_ema(prices, 12)
        ema26 = self._compute_ema(prices, 26)
        if not ema12 or not ema26:
            return None
        offset = len(ema12) - len(ema26)
        macd_line = [ema12[i + offset] - ema26[i] for i in range(len(ema26))]
        if len(macd_line) < 9:
            return None
        signal_line = self._compute_ema(macd_line, 9)
        if not signal_line:
            return None
        macd_val = macd_line[-1]
        signal_val = signal_line[-1]
        histogram = macd_val - signal_val
        return {
            'macd': round(macd_val, 4),
            'signal': round(signal_val, 4),
            'histogram': round(histogram, 4),
            'trend': 'bullish' if histogram > 0 else 'bearish',
        }

    def _compute_bollinger_bands(self, prices: List[float], window: int = 20) -> Optional[Dict[str, float]]:
        """Bollinger Bands (SMA ± 2σ) over `window` periods."""
        if len(prices) < window:
            return None
        recent = prices[-window:]
        sma = sum(recent) / window
        variance = sum((p - sma) ** 2 for p in recent) / window
        std = variance ** 0.5
        return {
            'upper': round(sma + 2 * std, 2),
            'middle': round(sma, 2),
            'lower': round(sma - 2 * std, 2),
            'bandwidth': round((4 * std / sma) * 100, 2) if sma > 0 else 0.0,
        }

    def compute_technical_indicators(self, symbol: str, days: int = 180) -> Optional[Dict[str, Any]]:
        """
        Compute RSI, MACD, Bollinger Bands, SMAs, momentum, and support/resistance
        from historical OHLCV data. Returns None if insufficient data.

        Uses a 180-day lookback by default (up from 60) with a 35-day warmup
        buffer so MACD (which needs 34 bars) computes even for stocks that
        trade only a few times per week.  The minimum data threshold is 7
        trading days (down from 15) so partial indicators are still returned
        for thinly-traded PSX scrips.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days + 35)  # warmup buffer
        data = self.get_price_history(symbol, start_date, end_date, limit=days + 35)
        if not data or len(data) < 7:
            return None

        closes = [float(d['close']) for d in data if d.get('close')]
        volumes = [int(d.get('volume', 0)) for d in data]
        if len(closes) < 7:
            return None

        result: Dict[str, Any] = {
            'symbol': symbol,
            'data_points': len(closes),
            'latest_price': closes[-1],
            'latest_date': data[-1].get('date'),
        }

        # SMAs
        for period, key in [(7, 'sma_7'), (14, 'sma_14'), (30, 'sma_30')]:
            if len(closes) >= period:
                result[key] = round(sum(closes[-period:]) / period, 2)

        # RSI
        rsi = self._compute_rsi(closes)
        if rsi is not None:
            result['rsi'] = round(rsi, 2)
            result['rsi_signal'] = (
                'overbought' if rsi > 70 else ('oversold' if rsi < 30 else 'neutral')
            )

        # MACD
        macd = self._compute_macd(closes)
        if macd:
            result['macd'] = macd

        # Bollinger Bands
        bb = self._compute_bollinger_bands(closes)
        if bb:
            result['bollinger_bands'] = bb
            price = closes[-1]
            if price >= bb['upper']:
                result['bb_signal'] = 'near_upper_band'
            elif price <= bb['lower']:
                result['bb_signal'] = 'near_lower_band'
            else:
                result['bb_signal'] = 'within_bands'

        # Volume trend: last 5 days vs previous 5 days
        if len(volumes) >= 10:
            recent_avg = sum(volumes[-5:]) / 5
            prev_avg = sum(volumes[-10:-5]) / 5
            if prev_avg > 0:
                vol_change = ((recent_avg - prev_avg) / prev_avg) * 100
                result['volume_trend'] = round(vol_change, 1)
                result['volume_signal'] = (
                    'increasing' if vol_change > 10 else
                    ('decreasing' if vol_change < -10 else 'stable')
                )

        # Price momentum (n-day returns)
        for n, key in [(5, 'momentum_5d'), (10, 'momentum_10d')]:
            if len(closes) >= n + 1:
                base = closes[-(n + 1)]
                if base > 0:
                    result[key] = round(((closes[-1] - base) / base) * 100, 2)

        # Support / Resistance from 30-day swing highs/lows
        recent_data = data[-30:]
        highs = [float(d.get('high', d.get('close', 0))) for d in recent_data]
        lows = [float(d.get('low', d.get('close', 0))) for d in recent_data]
        if highs:
            result['resistance'] = round(max(highs), 2)
        if lows:
            result['support'] = round(min(lows), 2)

        # Composite signal from RSI, MACD, SMA crossover, and momentum
        signals = []
        rsi_val = result.get('rsi')
        if rsi_val is not None:
            signals.append('bullish' if rsi_val < 40 else ('bearish' if rsi_val > 60 else 'neutral'))
        if macd:
            signals.append('bullish' if macd['histogram'] > 0 else 'bearish')
        if result.get('sma_7') and result.get('sma_30'):
            signals.append('bullish' if result['sma_7'] > result['sma_30'] else 'bearish')
        if result.get('momentum_5d') is not None:
            signals.append('bullish' if result['momentum_5d'] > 0 else 'bearish')

        if signals:
            bull = signals.count('bullish')
            bear = signals.count('bearish')
            total = len(signals)
            if bull > bear:
                result['overall_signal'] = 'bullish'
                result['signal_strength'] = round((bull / total) * 100)
            elif bear > bull:
                result['overall_signal'] = 'bearish'
                result['signal_strength'] = round((bear / total) * 100)
            else:
                result['overall_signal'] = 'neutral'
                result['signal_strength'] = 50

        return result

    def generate_prediction_context(self, symbol: str, target_date: Optional[date] = None) -> str:
        """
        Build a structured technical-analysis block ready for LLM prediction prompts.
        Fetches and computes indicators from Supabase OHLCV data.

        Falls back to a raw-stats block when full indicator computation is not
        possible (too few trading days), so the LLM always receives *some*
        numerical grounding rather than an "unavailable" dead-end string.
        """
        indicators = self.compute_technical_indicators(symbol)
        if not indicators:
            # Fallback: try to build a minimal stats block from raw price history
            stats = self.get_price_stats(symbol, days=90)
            if not stats:
                return (
                    f"## Technical Analysis: {symbol} — No Data Available\n"
                    f"No historical price data found in the Supabase stock_prices table for "
                    f"{symbol}. This symbol may not be tracked yet or may have an alternate "
                    f"ticker.  Please verify the PSX ticker and retry."
                )
            lines = [
                f"## Technical Analysis: {symbol} (Limited Data — Stats Only)",
                f"**Note:** Fewer than 7 trading days of OHLCV data available; "
                f"full indicator computation skipped.  Using 90-day price statistics instead.",
                f"**Latest Close:** PKR {stats['latest_close']:.2f}  (as of {stats.get('latest_date', 'N/A')})",
                f"**90-Day Range:** PKR {stats['min_close']:.2f} – PKR {stats['max_close']:.2f}",
                f"**90-Day Change:** {stats.get('change_percent', 0):+.2f}%  "
                f"(Trend: {stats.get('trend', 'stable').upper()})",
                f"**Avg Daily Volume:** {stats.get('avg_volume', 0):,.0f} shares",
            ]
            if target_date:
                days_ahead = (target_date - date.today()).days
                lines.append(
                    f"\n### Prediction Horizon: {target_date.strftime('%B %d, %Y')} "
                    f"({days_ahead} day(s) from today)"
                )
            return "\n".join(lines)

        stats = self.get_price_stats(symbol, days=30)
        price = indicators['latest_price']
        lines = [f"## Technical Analysis: {symbol} (Prediction Context)"]
        lines.append(f"**Latest Price:** PKR {price:.2f}  (as of {indicators['latest_date']})")

        if stats:
            chg = stats.get('change_percent', 0)
            lo = stats.get('min_close', 0)
            hi = stats.get('max_close', 0)
            lines.append(f"**30-Day Performance:** {chg:+.2f}%  |  Range: PKR {lo:.2f} – PKR {hi:.2f}")

        # Moving averages
        lines.append("\n### Moving Averages")
        for period, key in [(7, 'sma_7'), (14, 'sma_14'), (30, 'sma_30')]:
            val = indicators.get(key)
            if val:
                direction = "ABOVE" if price > val else "BELOW"
                diff_pct = ((price - val) / val * 100) if val > 0 else 0
                lines.append(f"- SMA{period}: PKR {val:.2f}  →  Price {direction} by {abs(diff_pct):.1f}%")

        # RSI
        rsi = indicators.get('rsi')
        if rsi is not None:
            sig = indicators.get('rsi_signal', '').upper()
            lines.append(f"\n### RSI (14-period): {rsi:.1f}  [{sig}]")
            lines.append("  (>70 = overbought / sell pressure  |  <30 = oversold / buy pressure)")

        # MACD
        macd = indicators.get('macd')
        if macd:
            lines.append(
                f"\n### MACD:  {macd['macd']:+.4f}  |  Signal: {macd['signal']:+.4f}  "
                f"|  Histogram: {macd['histogram']:+.4f}  [{macd['trend'].upper()}]"
            )

        # Bollinger Bands
        bb = indicators.get('bollinger_bands')
        if bb:
            bb_sig = indicators.get('bb_signal', 'within_bands').replace('_', ' ')
            lines.append(
                f"\n### Bollinger Bands (20-period):  "
                f"Upper PKR {bb['upper']:.2f}  |  Mid PKR {bb['middle']:.2f}  |  Lower PKR {bb['lower']:.2f}"
            )
            lines.append(f"  Price position: {bb_sig}  (bandwidth: {bb.get('bandwidth', 0):.1f}%)")

        # Support / Resistance
        sup = indicators.get('support')
        res = indicators.get('resistance')
        if sup and res:
            lines.append(f"\n### Key Levels (30-day):  Support PKR {sup:.2f}  |  Resistance PKR {res:.2f}")

        # Volume
        if 'volume_signal' in indicators:
            lines.append(
                f"\n### Volume Trend: {indicators.get('volume_trend', 0):+.1f}%  "
                f"[{indicators['volume_signal'].upper()}]"
            )

        # Momentum
        m5 = indicators.get('momentum_5d')
        m10 = indicators.get('momentum_10d')
        if m5 is not None:
            m10_str = f"{m10:+.2f}%" if m10 is not None else "N/A"
            lines.append(f"\n### Momentum:  5-day {m5:+.2f}%  |  10-day {m10_str}")

        # Overall signal
        sig = indicators.get('overall_signal', 'neutral')
        strength = indicators.get('signal_strength', 50)
        lines.append(
            f"\n### Overall Technical Signal: **{sig.upper()}**  "
            f"({strength}% of indicators agree)"
        )

        # Target date context
        if target_date:
            days_ahead = (target_date - date.today()).days
            if days_ahead <= 2:
                horizon = "very short-term (1-2 days)"
            elif days_ahead <= 7:
                horizon = "short-term (up to 1 week)"
            elif days_ahead <= 14:
                horizon = "medium-term (1-2 weeks)"
            else:
                horizon = "medium/long-term (2+ weeks)"
            lines.append(
                f"\n### Prediction Horizon:  {target_date.strftime('%B %d, %Y')}  "
                f"({days_ahead} day(s) from today — {horizon})"
            )

        return "\n".join(lines)

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
