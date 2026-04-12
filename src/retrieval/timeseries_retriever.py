"""
Time Series Retriever for fetching numeric data.
Retrieves data from timeseries_points and series_registry tables.
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.categories import SectorCategory, TimeSeriesType
from src.db.connection import get_supabase_client
from config.settings import get_settings


class TimeSeriesRetriever:
    """
    Retriever for time-series data.
    
    Provides methods for:
    - Getting latest values
    - Fetching historical data
    - Computing statistics
    - Finding related series
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.settings = get_settings()
    
    # =========================================================================
    # SERIES LOOKUP
    # =========================================================================
    
    def find_series(
        self,
        symbol: Optional[str] = None,
        provider: Optional[str] = None,
        sector: Optional[SectorCategory] = None,
        series_type: Optional[TimeSeriesType] = None
    ) -> List[Dict[str, Any]]:
        """
        Find series matching criteria.
        
        Args:
            symbol: Partial or full symbol match
            provider: Data provider
            sector: Sector category
            series_type: Series type
            
        Returns:
            List of matching series from registry
        """
        query = self.supabase.table("series_registry").select("*")
        
        if symbol:
            query = query.ilike("symbol", f"%{symbol}%")
        if provider:
            query = query.eq("provider", provider)
        if sector:
            query = query.eq("sector_category", sector.value)
        if series_type:
            query = query.eq("series_type", series_type.value)
        
        result = query.execute()
        return result.data or []
    
    def get_series_by_id(self, series_id: str) -> Optional[Dict[str, Any]]:
        """Get series metadata by ID."""
        result = self.supabase.table("series_registry").select("*").eq(
            "series_id", series_id
        ).execute()
        
        if result.data:
            return result.data[0]
        return None
    
    # =========================================================================
    # DATA RETRIEVAL
    # =========================================================================
    
    def get_latest(self, series_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent data point for a series.
        
        Args:
            series_id: Series identifier
            
        Returns:
            Latest data point or None
        """
        result = self.supabase.rpc("get_latest_value", {
            "target_series_id": series_id
        }).execute()
        
        if result.data:
            return result.data[0]
        return None
    
    def get_range(
        self,
        series_id: str,
        start: datetime,
        end: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get data points within a time range.
        
        Args:
            series_id: Series identifier
            start: Start datetime
            end: End datetime (defaults to now)
            
        Returns:
            List of data points
        """
        end = end or datetime.utcnow()
        
        result = self.supabase.rpc("get_series_range", {
            "target_series_id": series_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat()
        }).execute()
        
        return result.data or []
    
    def get_stats(
        self,
        series_id: str,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Get aggregated statistics for a series.
        
        Args:
            series_id: Series identifier
            days: Number of days to analyze
            
        Returns:
            Stats dict with min, max, avg, etc.
        """
        start = datetime.utcnow() - timedelta(days=days)
        
        result = self.supabase.rpc("get_series_stats", {
            "target_series_id": series_id,
            "start_time": start.isoformat()
        }).execute()
        
        if result.data:
            return result.data[0]
        return None
    
    # =========================================================================
    # MULTI-SERIES QUERIES
    # =========================================================================
    
    def get_latest_multiple(
        self, 
        series_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get latest values for multiple series.
        
        Args:
            series_ids: List of series identifiers
            
        Returns:
            Dict mapping series_id to latest point
        """
        results = {}
        for sid in series_ids:
            latest = self.get_latest(sid)
            if latest:
                results[sid] = latest
        return results
    
    def get_sector_summary(
        self, 
        sector: SectorCategory,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get summary of latest values for a sector.
        
        Args:
            sector: Sector category
            limit: Max series to return
            
        Returns:
            List of series with their latest values
        """
        # Get series in sector
        series_list = self.find_series(sector=sector)[:limit]
        
        summaries = []
        for series in series_list:
            latest = self.get_latest(series["series_id"])
            if latest:
                summaries.append({
                    "series_id": series["series_id"],
                    "symbol": series["symbol"],
                    "metric": series["metric"],
                    "subcategory": series.get("subcategory"),
                    "latest_value": latest.get("value"),
                    "latest_timestamp": latest.get("timestamp"),
                    "unit": latest.get("unit")
                })
        
        return summaries
    
    # =========================================================================
    # TREND ANALYSIS
    # =========================================================================
    
    def get_trend(
        self,
        series_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get trend information for a series.
        
        Args:
            series_id: Series identifier
            days: Number of days to analyze
            
        Returns:
            Trend analysis dict
        """
        stats = self.get_stats(series_id, days)
        if not stats:
            return {"error": "No data available"}
        
        latest = self.get_latest(series_id)
        
        # Get data for trend calculation
        start = datetime.utcnow() - timedelta(days=days)
        data = self.get_range(series_id, start)
        
        if len(data) < 2:
            return {
                "series_id": series_id,
                "period_days": days,
                "data_points": len(data),
                "trend": "insufficient_data"
            }
        
        # Calculate simple trend
        first_value = data[0].get("value", 0)
        last_value = data[-1].get("value", 0)
        
        if first_value == 0:
            change_pct = 0
        else:
            change_pct = ((last_value - first_value) / first_value) * 100
        
        trend_direction = "up" if change_pct > 1 else "down" if change_pct < -1 else "stable"
        
        return {
            "series_id": series_id,
            "period_days": days,
            "data_points": len(data),
            "first_value": first_value,
            "last_value": last_value,
            "min_value": stats.get("min_value"),
            "max_value": stats.get("max_value"),
            "avg_value": stats.get("avg_value"),
            "change_absolute": last_value - first_value,
            "change_percent": round(change_pct, 2),
            "trend": trend_direction
        }
    
    # =========================================================================
    # FORMATTING FOR CONTEXT
    # =========================================================================
    
    def format_for_context(
        self,
        data: List[Dict[str, Any]],
        series_info: Dict[str, Any]
    ) -> str:
        """
        Format time-series data for LLM context.
        
        Args:
            data: List of data points
            series_info: Series metadata
            
        Returns:
            Formatted string
        """
        symbol = series_info.get("symbol", "Unknown")
        metric = series_info.get("metric", "value")
        unit = data[0].get("unit", "") if data else ""
        
        lines = [f"Time Series: {symbol} ({metric})"]
        lines.append(f"Unit: {unit}")
        lines.append(f"Points: {len(data)}")
        lines.append("---")
        
        # Show summary stats if enough data
        if len(data) >= 2:
            values = [d.get("value", 0) for d in data]
            lines.append(f"Latest: {values[-1]}")
            lines.append(f"Min: {min(values)}")
            lines.append(f"Max: {max(values)}")
            lines.append(f"Avg: {sum(values)/len(values):.2f}")
        
        # Show recent values (last 10)
        lines.append("---")
        lines.append("Recent values:")
        for point in data[-10:]:
            ts = point.get("timestamp", "")[:10]
            val = point.get("value", 0)
            lines.append(f"  {ts}: {val}")
        
        return "\n".join(lines)
    
    def format_comparison(
        self,
        series_data: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Format multiple series for comparison.
        
        Args:
            series_data: Dict mapping series_id to data points
            
        Returns:
            Formatted comparison string
        """
        if not series_data:
            return "No data available for comparison."
        
        lines = ["Series Comparison:"]
        lines.append("=" * 40)
        
        for series_id, data in series_data.items():
            if not data:
                continue
            
            latest = data[-1] if data else {}
            values = [d.get("value", 0) for d in data]
            
            lines.append(f"\n{series_id}:")
            lines.append(f"  Latest: {latest.get('value', 'N/A')}")
            lines.append(f"  Points: {len(data)}")
            
            if len(values) >= 2:
                change = values[-1] - values[0]
                pct = (change / values[0] * 100) if values[0] != 0 else 0
                lines.append(f"  Change: {change:+.2f} ({pct:+.1f}%)")
        
        return "\n".join(lines)
