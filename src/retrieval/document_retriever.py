"""
Document Retriever using Qdrant for vector search.
Retrieves relevant documents from Qdrant + Supabase.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.categories import SectorCategory, WebSourceType
from src.db.connection import get_supabase_client
from src.db.qdrant_client import QdrantService
from src.ingestion.embeddings import EmbeddingService
from config.settings import get_settings


class DocumentRetriever:
    """
    Retriever for finding relevant documents using Qdrant vector similarity.
    
    Process:
    1. Generate query embedding
    2. Search Qdrant for similar vectors (returns doc UUIDs)
    3. Fetch full documents from Supabase using UUIDs
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.qdrant = QdrantService()
        self.embedding_service = EmbeddingService()
        self.settings = get_settings()
    
    def search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        sector_category: Optional[SectorCategory] = None,
        source_type: Optional[WebSourceType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using vector similarity.
        
        Args:
            query: Search query string
            limit: Maximum results to return
            threshold: Minimum similarity threshold (0-1)
            sector_category: Filter by sector
            source_type: Filter by source type
            start_date: Filter by publication date (start)
            end_date: Filter by publication date (end)
            
        Returns:
            List of matching documents with similarity scores
        """
        # Generate query embedding using retrieval_query task type
        query_embedding = self.embedding_service.embed_query(query)
        
        # Search Qdrant
        vector_results = self.qdrant.search(
            query_vector=query_embedding,
            limit=limit * 2,  # Get more to account for date filtering
            score_threshold=threshold,
            sector_category=sector_category.value if sector_category else None,
            source_type=source_type.value if source_type else None
        )
        
        if not vector_results:
            return []
        
        # Get doc UUIDs
        doc_ids = [r["doc_id"] for r in vector_results]
        
        # Fetch full documents from Supabase
        result = self.supabase.table("documents").select("*").in_(
            "id", doc_ids
        ).execute()
        
        # Create lookup by UUID
        docs_by_id = {doc["id"]: doc for doc in result.data}
        
        # Merge with similarity scores and maintain order
        documents = []
        for vec_result in vector_results:
            doc_id = vec_result["doc_id"]
            if doc_id in docs_by_id:
                doc = docs_by_id[doc_id]
                doc["similarity"] = vec_result["score"]
                
                # Apply date filters if specified
                if start_date or end_date:
                    pub_date = doc.get("published_at")
                    if pub_date:
                        pub_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                        if start_date and pub_dt < start_date:
                            continue
                        if end_date and pub_dt > end_date:
                            continue
                
                documents.append(doc)
                
                if len(documents) >= limit:
                    break
        
        return documents
    
    def search_by_sector(
        self,
        query: str,
        sector: SectorCategory,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search within a specific sector.
        
        Args:
            query: Search query
            sector: Sector to filter by
            limit: Max results
            
        Returns:
            List of matching documents
        """
        return self.search(
            query=query,
            limit=limit,
            sector_category=sector
        )
    
    def search_recent(
        self,
        query: str,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search recent documents.
        
        Args:
            query: Search query
            days: Number of days back
            limit: Max results
            
        Returns:
            List of matching documents
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        return self.search(
            query=query,
            limit=limit,
            start_date=start_date
        )
    
    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by its UUID."""
        result = self.supabase.table("documents").select("*").eq(
            "id", doc_id
        ).execute()
        
        if result.data:
            return result.data[0]
        return None
    
    def list_by_sector(
        self,
        sector: SectorCategory,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List documents by sector category.
        
        Args:
            sector: Sector to filter by
            limit: Max results per page
            offset: Pagination offset
            
        Returns:
            List of documents
        """
        result = self.supabase.table("documents").select(
            "id, source_type, sector_category, subcategory, title, url, published_at"
        ).eq(
            "sector_category", sector.value
        ).order(
            "published_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        
        return result.data or []
    
    def list_by_source_type(
        self,
        source_type: WebSourceType,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List documents by source type.
        
        Args:
            source_type: Source type to filter by
            limit: Max results per page
            offset: Pagination offset
            
        Returns:
            List of documents
        """
        result = self.supabase.table("documents").select(
            "id, source_type, sector_category, subcategory, title, url, published_at"
        ).eq(
            "source_type", source_type.value
        ).order(
            "published_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        
        return result.data or []
    
    def format_for_context(
        self, 
        documents: List[Dict[str, Any]],
        max_length: int = 4000
    ) -> str:
        """
        Format documents for inclusion in LLM context.
        
        Args:
            documents: List of document dicts
            max_length: Maximum total character length
            
        Returns:
            Formatted context string
        """
        context_parts = []
        current_length = 0
        
        for i, doc in enumerate(documents, 1):
            title = doc.get("title", "Untitled")
            content = doc.get("content", "")
            url = doc.get("url", "")
            sector = doc.get("sector_category", "")
            similarity = doc.get("similarity", 0)
            
            entry = f"""
[Source {i}] {title}
Sector: {sector}
Relevance: {similarity:.2f}
{content[:500]}...
URL: {url}
"""
            if current_length + len(entry) > max_length:
                break
            
            context_parts.append(entry)
            current_length += len(entry)
        
        return "\n---\n".join(context_parts)
