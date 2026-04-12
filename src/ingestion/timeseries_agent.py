"""
Time Series Agent for ingesting live and historical numeric data.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Generator
import httpx
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.categories import TimeSeriesType, SectorCategory, normalize_subcategory
from src.db.models import SeriesRegistry, TimeSeriesPoint
from src.db.connection import get_supabase_client
from config.settings import get_settings


class TimeSeriesAgent:
    """
    Agent for ingesting time-series data into the database.
    
    Responsibilities:
    1. Manage series registry (metadata)
    2. Fetch data from providers (PSX, FX, etc.)
    3. Assign series_type (agent category)
    4. Store points in timeseries_points table
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.settings = get_settings()
        self.client = httpx.Client(timeout=30.0)
    
    # =========================================================================
    # SERIES REGISTRY MANAGEMENT
    # =========================================================================
    
    def register_series(
        self,
        provider: str,
        symbol: str,
        metric: str,
        frequency: str,
        series_type: TimeSeriesType,
        sector_category: Optional[SectorCategory] = None,
        subcategory: Optional[str] = None,
        timezone: str = "Asia/Karachi"
    ) -> SeriesRegistry:
        """
        Register a new time series in the registry.
        
        Args:
            provider: Data provider (e.g., 'psx', 'sbp', 'forex')
            symbol: Symbol/ticker (e.g., 'OGDC', 'USD_PKR')
            metric: Metric name (e.g., 'close', 'rate')
            frequency: Data frequency (e.g., '1m', '1h', '1d')
            series_type: Agent category (NEVER a sector category)
            sector_category: Economic domain (optional)
            subcategory: Specific subcategory (optional)
            timezone: Timezone for timestamps
            
        Returns:
            Created SeriesRegistry object
        """
        series_id = SeriesRegistry.generate_series_id(
            provider, symbol, metric, frequency
        )
        
        registry = SeriesRegistry(
            series_id=series_id,
            series_type=series_type,
            provider=provider,
            symbol=symbol,
            metric=metric,
            frequency=frequency,
            timezone=timezone,
            sector_category=sector_category,
            subcategory=subcategory
        )
        
        # Upsert to database
        self.supabase.table("series_registry").upsert(
            registry.to_db_dict(),
            on_conflict="series_id"
        ).execute()
        
        return registry
    
    def get_series(self, series_id: str) -> Optional[SeriesRegistry]:
        """Get a series from the registry."""
        result = self.supabase.table("series_registry").select("*").eq(
            "series_id", series_id
        ).execute()
        
        if result.data:
            data = result.data[0]
            return SeriesRegistry(
                series_id=data["series_id"],
                series_type=TimeSeriesType(data["series_type"]),
                provider=data["provider"],
                symbol=data["symbol"],
                metric=data["metric"],
                frequency=data["frequency"],
                timezone=data.get("timezone", "Asia/Karachi"),
                sector_category=SectorCategory(data["sector_category"]) if data.get("sector_category") else None,
                subcategory=data.get("subcategory"),
                created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
            )
        return None
    
    def list_series(
        self,
        provider: Optional[str] = None,
        sector_category: Optional[SectorCategory] = None,
        series_type: Optional[TimeSeriesType] = None
    ) -> List[SeriesRegistry]:
        """List series from registry with optional filters."""
        query = self.supabase.table("series_registry").select("*")
        
        if provider:
            query = query.eq("provider", provider)
        if sector_category:
            query = query.eq("sector_category", sector_category.value)
        if series_type:
            query = query.eq("series_type", series_type.value)
        
        result = query.execute()
        
        registries = []
        for data in result.data:
            registries.append(SeriesRegistry(
                series_id=data["series_id"],
                series_type=TimeSeriesType(data["series_type"]),
                provider=data["provider"],
                symbol=data["symbol"],
                metric=data["metric"],
                frequency=data["frequency"],
                timezone=data.get("timezone", "Asia/Karachi"),
                sector_category=SectorCategory(data["sector_category"]) if data.get("sector_category") else None,
                subcategory=data.get("subcategory"),
                created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
            ))
        
        return registries
    
    # =========================================================================
    # DATA POINT INGESTION
    # =========================================================================
    
    def ingest_point(
        self,
        series_id: str,
        timestamp: datetime,
        value: float,
        unit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TimeSeriesPoint:
        """
        Ingest a single data point.
        
        Args:
            series_id: Reference to series_registry
            timestamp: Point timestamp
            value: Numeric value
            unit: Unit of measurement (optional)
            metadata: Additional data
            
        Returns:
            Created TimeSeriesPoint
        """
        # Get series info from registry
        series = self.get_series(series_id)
        if not series:
            raise ValueError(f"Series not found: {series_id}")
        
        point = TimeSeriesPoint(
            series_id=series_id,
            series_type=series.series_type,
            sector_category=series.sector_category,
            subcategory=series.subcategory,
            timestamp=timestamp,
            value=value,
            unit=unit,
            provider=series.provider,
            metadata=metadata or {}
        )
        
        # Insert into database
        self.supabase.table("timeseries_points").upsert(
            point.to_db_dict(),
            on_conflict="series_id,timestamp"
        ).execute()
        
        return point
    
    def ingest_points(
        self,
        series_id: str,
        points: List[Dict[str, Any]]
    ) -> int:
        """
        Ingest multiple data points for a series.
        
        Args:
            series_id: Reference to series_registry
            points: List of dicts with 'timestamp', 'value', optional 'unit'
            
        Returns:
            Number of points ingested
        """
        series = self.get_series(series_id)
        if not series:
            raise ValueError(f"Series not found: {series_id}")
        
        records = []
        for p in points:
            point = TimeSeriesPoint(
                series_id=series_id,
                series_type=series.series_type,
                sector_category=series.sector_category,
                subcategory=series.subcategory,
                timestamp=p["timestamp"],
                value=p["value"],
                unit=p.get("unit"),
                provider=series.provider,
                metadata=p.get("metadata", {})
            )
            records.append(point.to_db_dict())
        
        # Batch upsert
        if records:
            self.supabase.table("timeseries_points").upsert(
                records,
                on_conflict="series_id,timestamp"
            ).execute()
        
        return len(records)
    
    # =========================================================================
    # PROVIDER INTEGRATIONS (Example implementations)
    # =========================================================================
    
    def fetch_psx_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch stock data from PSX.
        
        This is a placeholder - implement actual PSX API integration.
        """
        # Example implementation pattern
        # In production, use actual PSX API
        
        # Ensure series is registered
        series_id = SeriesRegistry.generate_series_id(
            "psx", symbol, "close", "1d"
        )
        
        if not self.get_series(series_id):
            # Auto-register if not exists
            self.register_series(
                provider="psx",
                symbol=symbol,
                metric="close",
                frequency="1d",
                series_type=TimeSeriesType.END_OF_DAY_BATCH,
                sector_category=SectorCategory.STOCKS,
                subcategory=symbol.lower()
            )
        
        # Placeholder for actual API call
        # points = self._call_psx_api(symbol, start_date, end_date)
        # self.ingest_points(series_id, points)
        
        return []
    
    def fetch_forex_data(
        self,
        base: str,
        quote: str,
        frequency: str = "1d"
    ) -> List[Dict[str, Any]]:
        """
        Fetch forex data.
        
        This is a placeholder - implement actual forex API integration.
        """
        symbol = f"{base}_{quote}".upper()
        series_id = SeriesRegistry.generate_series_id(
            "forex", symbol, "rate", frequency
        )
        
        if not self.get_series(series_id):
            self.register_series(
                provider="forex",
                symbol=symbol,
                metric="rate",
                frequency=frequency,
                series_type=TimeSeriesType.END_OF_DAY_BATCH if frequency == "1d" else TimeSeriesType.INTERVAL_SNAPSHOT,
                sector_category=SectorCategory.CURRENCY_FX,
                subcategory=symbol.lower()
            )
        
        # Placeholder for actual API call
        return []
    
    def fetch_sbp_rate(
        self,
        rate_type: str = "policy_rate"
    ) -> List[Dict[str, Any]]:
        """
        Fetch SBP rates (policy rate, KIBOR, etc.).
        
        This is a placeholder - implement actual SBP data integration.
        """
        series_id = SeriesRegistry.generate_series_id(
            "sbp", rate_type, "rate", "1d"
        )
        
        if not self.get_series(series_id):
            self.register_series(
                provider="sbp",
                symbol=rate_type,
                metric="rate",
                frequency="1d",
                series_type=TimeSeriesType.DAILY_INDICATOR,
                sector_category=SectorCategory.BANKING,
                subcategory=normalize_subcategory(rate_type)
            )
        
        return []
    
    # =========================================================================
    # QUERY OPERATIONS
    # =========================================================================
    
    def get_latest(self, series_id: str) -> Optional[TimeSeriesPoint]:
        """Get the most recent data point for a series."""
        result = self.supabase.table("timeseries_points").select("*").eq(
            "series_id", series_id
        ).order("timestamp", desc=True).limit(1).execute()
        
        if result.data:
            data = result.data[0]
            return TimeSeriesPoint(
                id=data["id"],
                series_id=data["series_id"],
                series_type=TimeSeriesType(data["series_type"]),
                sector_category=SectorCategory(data["sector_category"]) if data.get("sector_category") else None,
                subcategory=data.get("subcategory"),
                timestamp=datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00')),
                value=data["value"],
                unit=data.get("unit"),
                provider=data["provider"],
                metadata=data.get("metadata", {})
            )
        return None
    
    def get_range(
        self,
        series_id: str,
        start: datetime,
        end: Optional[datetime] = None
    ) -> List[TimeSeriesPoint]:
        """Get data points within a time range."""
        end = end or datetime.utcnow()
        
        result = self.supabase.table("timeseries_points").select("*").eq(
            "series_id", series_id
        ).gte("timestamp", start.isoformat()).lte(
            "timestamp", end.isoformat()
        ).order("timestamp", desc=False).execute()
        
        points = []
        for data in result.data:
            points.append(TimeSeriesPoint(
                id=data["id"],
                series_id=data["series_id"],
                series_type=TimeSeriesType(data["series_type"]),
                sector_category=SectorCategory(data["sector_category"]) if data.get("sector_category") else None,
                subcategory=data.get("subcategory"),
                timestamp=datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00')),
                value=data["value"],
                unit=data.get("unit"),
                provider=data["provider"],
                metadata=data.get("metadata", {})
            ))
        
        return points
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
