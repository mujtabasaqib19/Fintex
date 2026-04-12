"""Ingestion module for web and time-series data."""
from .web_agent import WebSearchAgent
from .timeseries_agent import TimeSeriesAgent
from .embeddings import EmbeddingService

__all__ = ["WebSearchAgent", "TimeSeriesAgent", "EmbeddingService"]
