"""
Pydantic models for database records.
Enforces the separation between agent categories and sector categories.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.categories import (
    SectorCategory, WebSourceType, TimeSeriesType,
    validate_sector_category, validate_no_sector_in_agent_type,
    normalize_subcategory, get_sector_categories
)


# =============================================================================
# DOCUMENT MODEL (Web-Search Content)
# =============================================================================
class Document(BaseModel):
    """
    Model for web-search content stored in the 'documents' table.
    
    Rules:
    - source_type: MUST be a WebSourceType (agent category)
    - sector_category: MUST be a SectorCategory (economic domain)
    - These fields are NEVER interchangeable
    """
    id: Optional[str] = None
    
    # Agent category (data type/collection intent)
    source_type: WebSourceType = Field(
        ...,
        description="Type of web content (agent category). Never a sector category."
    )
    
    # Economic domain (optional, can be inferred)
    sector_category: Optional[SectorCategory] = Field(
        None,
        description="Economic sector. Must be one of the 11 fixed categories."
    )
    
    # Dynamic subcategory (normalized snake_case)
    subcategory: Optional[str] = Field(
        None,
        description="Dynamic subcategory (e.g., cement, kibor, kse100)"
    )
    
    # Content fields
    title: str
    content: str
    url: Optional[str] = None
    source_filename: Optional[str] = None
    
    # Timestamps
    published_at: Optional[datetime] = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional data
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('subcategory')
    @classmethod
    def normalize_subcategory_field(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_subcategory(v)
    
    @field_validator('source_type')
    @classmethod
    def validate_source_type(cls, v: WebSourceType) -> WebSourceType:
        """Ensure source_type is not a sector category."""
        if v.value in get_sector_categories():
            raise ValueError(f"source_type cannot be a sector category: {v.value}")
        return v
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        data = {
            "source_type": self.source_type.value,
            "title": self.title,
            "content": self.content,
            "ingested_at": self.ingested_at.isoformat(),
            "metadata": self.metadata,
        }
        if self.sector_category:
            data["sector_category"] = self.sector_category.value
        if self.subcategory:
            data["subcategory"] = self.subcategory
        if self.url:
            data["url"] = self.url
        if self.source_filename:
            data["source_filename"] = self.source_filename
        if self.published_at:
            data["published_at"] = self.published_at.isoformat()
        return data


# =============================================================================
# SERIES REGISTRY MODEL (Time-Series Metadata)
# =============================================================================
class SeriesRegistry(BaseModel):
    """
    Model for time-series metadata stored in 'series_registry' table.
    Defines a series once for lookup.
    """
    series_id: str = Field(
        ...,
        description="Stable identifier: provider:symbol:metric:freq"
    )
    
    # Agent category
    series_type: TimeSeriesType = Field(
        ...,
        description="Type of time-series (agent category). Never a sector category."
    )
    
    # Provider info
    provider: str = Field(..., description="Data provider (e.g., psx, sbp, forex)")
    symbol: str = Field(..., description="Symbol/ticker (e.g., OGDC, USD_PKR)")
    metric: str = Field(..., description="Metric name (e.g., close, open, rate)")
    frequency: str = Field(..., description="Data frequency (e.g., 1m, 1h, 1d)")
    timezone: str = Field(default="Asia/Karachi")
    
    # Economic domain (optional)
    sector_category: Optional[SectorCategory] = None
    subcategory: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('subcategory')
    @classmethod
    def normalize_subcategory_field(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_subcategory(v)
    
    @field_validator('series_type')
    @classmethod
    def validate_series_type(cls, v: TimeSeriesType) -> TimeSeriesType:
        """Ensure series_type is not a sector category."""
        if v.value in get_sector_categories():
            raise ValueError(f"series_type cannot be a sector category: {v.value}")
        return v
    
    @classmethod
    def generate_series_id(cls, provider: str, symbol: str, metric: str, freq: str) -> str:
        """Generate a stable series_id."""
        return f"{provider}:{symbol}:{metric}:{freq}".lower()
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        data = {
            "series_id": self.series_id,
            "series_type": self.series_type.value,
            "provider": self.provider,
            "symbol": self.symbol,
            "metric": self.metric,
            "frequency": self.frequency,
            "timezone": self.timezone,
            "created_at": self.created_at.isoformat(),
        }
        if self.sector_category:
            data["sector_category"] = self.sector_category.value
        if self.subcategory:
            data["subcategory"] = self.subcategory
        return data


# =============================================================================
# TIME SERIES POINT MODEL (Numeric Data)
# =============================================================================
class TimeSeriesPoint(BaseModel):
    """
    Model for time-series data points stored in 'timeseries_points' table.
    """
    id: Optional[str] = None
    
    # Reference to registry
    series_id: str = Field(
        ...,
        description="Reference to series_registry.series_id"
    )
    
    # Agent category (redundant but useful for queries)
    series_type: TimeSeriesType = Field(
        ...,
        description="Type of time-series (agent category). Never a sector category."
    )
    
    # Economic domain (optional, can be copied from registry)
    sector_category: Optional[SectorCategory] = None
    subcategory: Optional[str] = None
    
    # Data point
    timestamp: datetime
    value: float
    unit: Optional[str] = None
    
    # Source
    provider: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('subcategory')
    @classmethod
    def normalize_subcategory_field(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_subcategory(v)
    
    @field_validator('series_type')
    @classmethod
    def validate_series_type(cls, v: TimeSeriesType) -> TimeSeriesType:
        """Ensure series_type is not a sector category."""
        if v.value in get_sector_categories():
            raise ValueError(f"series_type cannot be a sector category: {v.value}")
        return v
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        data = {
            "series_id": self.series_id,
            "series_type": self.series_type.value,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "provider": self.provider,
            "metadata": self.metadata,
        }
        if self.sector_category:
            data["sector_category"] = self.sector_category.value
        if self.subcategory:
            data["subcategory"] = self.subcategory
        if self.unit:
            data["unit"] = self.unit
        return data


# =============================================================================
# BATCH MODELS FOR BULK OPERATIONS
# =============================================================================
class DocumentBatch(BaseModel):
    """Batch of documents for bulk insertion."""
    documents: List[Document]
    
    def to_db_list(self) -> List[Dict[str, Any]]:
        return [doc.to_db_dict() for doc in self.documents]


class TimeSeriesPointBatch(BaseModel):
    """Batch of time-series points for bulk insertion."""
    points: List[TimeSeriesPoint]
    
    def to_db_list(self) -> List[Dict[str, Any]]:
        return [point.to_db_dict() for point in self.points]
