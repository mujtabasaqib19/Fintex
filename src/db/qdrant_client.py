"""
Qdrant vector database client.
Handles embedding storage and retrieval.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Optional, Dict, Any
from functools import lru_cache
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import get_settings


@lru_cache()
def get_qdrant_client() -> QdrantClient:
    """
    Get a cached Qdrant client instance.
    """
    settings = get_settings()
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )


class QdrantService:
    """
    Service for managing vectors in Qdrant.
    
    Key features:
    - Vector UUID matches Supabase document UUID
    - Stores minimal metadata (sector, source_type for filtering)
    - Main content stays in Supabase
    """
    
    def __init__(self):
        self.client = get_qdrant_client()
        self.settings = get_settings()
        self.collection_name = self.settings.qdrant_collection
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            # Gemini text-embedding-004 produces 768-dimensional vectors
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
    
    def upsert_vector(
        self,
        doc_id: str,
        embedding: List[float],
        sector_category: Optional[str] = None,
        source_type: Optional[str] = None,
        subcategory: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store or update a vector in Qdrant.
        
        Args:
            doc_id: UUID from Supabase (must match)
            embedding: Vector embedding
            sector_category: Economic sector for filtering
            source_type: Agent category for filtering
            subcategory: Subcategory for filtering
            metadata: Additional metadata for filtering
        """
        payload = {}
        
        if sector_category:
            payload["sector_category"] = sector_category
        if source_type:
            payload["source_type"] = source_type
        if subcategory:
            payload["subcategory"] = subcategory
        if metadata:
            payload.update(metadata)
        
        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload=payload
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        sector_category: Optional[str] = None,
        source_type: Optional[str] = None,
        subcategory: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query embedding
            limit: Max results
            score_threshold: Minimum similarity score (0-1)
            sector_category: Filter by sector
            source_type: Filter by source type
            subcategory: Filter by subcategory
            
        Returns:
            List of results with doc_id and score
        """
        # Build filter
        filter_conditions = []
        
        if sector_category:
            filter_conditions.append(
                FieldCondition(
                    key="sector_category",
                    match=MatchValue(value=sector_category)
                )
            )
        
        if source_type:
            filter_conditions.append(
                FieldCondition(
                    key="source_type",
                    match=MatchValue(value=source_type)
                )
            )
        
        if subcategory:
            filter_conditions.append(
                FieldCondition(
                    key="subcategory",
                    match=MatchValue(value=subcategory)
                )
            )
        
        query_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        
        # Use query_points instead of search (compatible with qdrant-client >= 1.16)
        # Note: 'query' arg replaces 'query_vector'
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True
        )
        
        # Extract points from QueryResponse
        results = response.points
        
        return [
            {
                "doc_id": str(hit.id),
                "score": hit.score,
                "sector_category": hit.payload.get("sector_category"),
                "source_type": hit.payload.get("source_type"),
                "subcategory": hit.payload.get("subcategory")
            }
            for hit in results
        ]
    
    def delete_vector(self, doc_id: str) -> None:
        """Delete a vector by document ID."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[doc_id]
        )
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics."""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": info.config.params.vectors.size,
            "vector_count": info.points_count,
            "status": info.status
        }
