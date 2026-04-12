"""
Web Search Agent for ingesting web content (news, PDFs, reports).
"""
import httpx
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from io import BytesIO
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.categories import WebSourceType, SectorCategory, normalize_subcategory
from src.db.models import Document
from src.db.connection import get_supabase_client
from src.db.qdrant_client import QdrantService
from src.ingestion.embeddings import EmbeddingService
from config.settings import get_settings


class WebSearchAgent:
    """
    Agent for ingesting web content into the documents table.
    
    Responsibilities:
    1. Fetch content from URLs or PDFs
    2. Extract and clean text
    3. Chunk content appropriately
    4. Assign source_type (agent category)
    5. Generate embeddings
    6. Store in documents table
    """
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.supabase = get_supabase_client()
        self.qdrant = QdrantService()
        self.embedding_service = EmbeddingService()
        self.settings = get_settings()
    
    # =========================================================================
    # CONTENT FETCHING
    # =========================================================================
    
    def fetch_url(self, url: str) -> Tuple[str, str]:
        """
        Fetch content from a URL.
        
        Returns:
            Tuple of (title, content)
        """
        response = self.client.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string or ""
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text content
        content = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)
        
        return title.strip(), content.strip()
    
    def fetch_pdf(self, pdf_source: str) -> Tuple[str, str]:
        """
        Extract text from a PDF file or URL.
        
        Args:
            pdf_source: Path to local PDF or URL
            
        Returns:
            Tuple of (filename/title, content)
        """
        if pdf_source.startswith('http'):
            response = self.client.get(pdf_source)
            response.raise_for_status()
            pdf_bytes = BytesIO(response.content)
            title = pdf_source.split('/')[-1]
        else:
            pdf_bytes = open(pdf_source, 'rb')
            title = os.path.basename(pdf_source)
        
        reader = PdfReader(pdf_bytes)
        
        content_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                content_parts.append(text)
        
        content = '\n\n'.join(content_parts)
        
        if hasattr(pdf_bytes, 'close'):
            pdf_bytes.close()
        
        return title, content
    
    # =========================================================================
    # TEXT CHUNKING
    # =========================================================================
    
    def chunk_text(
        self, 
        text: str, 
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Max characters per chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or self.settings.chunk_size
        chunk_overlap = chunk_overlap or self.settings.chunk_overlap
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end within last 100 chars
                last_period = text.rfind('.', end - 100, end)
                last_newline = text.rfind('\n', end - 100, end)
                break_point = max(last_period, last_newline)
                
                if break_point > start:
                    end = break_point + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - chunk_overlap
        
        return chunks
    
    # =========================================================================
    # SOURCE TYPE CLASSIFICATION
    # =========================================================================
    
    def classify_source_type(
        self, 
        url: str, 
        title: str, 
        content: str
    ) -> WebSourceType:
        """
        Classify the source type based on URL patterns and content.
        
        Returns:
            WebSourceType enum value (NEVER a sector category)
        """
        url_lower = url.lower()
        title_lower = title.lower()
        content_preview = content[:500].lower()
        
        # URL-based classification
        if any(x in url_lower for x in ['breaking', 'alert', 'flash']):
            return WebSourceType.BREAKING_UPDATE
        
        if any(x in url_lower for x in ['policy', 'regulation', 'sbp.org', 'secp.gov']):
            return WebSourceType.POLICY_DOCUMENT
        
        if any(x in url_lower for x in ['filing', 'disclosure', 'announcement']):
            return WebSourceType.REGULATORY_FILING
        
        if url_lower.endswith('.pdf'):
            # PDFs are usually reports or policy docs
            if any(x in title_lower for x in ['policy', 'circular', 'regulation']):
                return WebSourceType.POLICY_DOCUMENT
            return WebSourceType.INDUSTRY_REPORT
        
        # Content-based classification
        if any(x in title_lower for x in ['earnings', 'quarterly', 'q1', 'q2', 'q3', 'q4', 'annual report']):
            return WebSourceType.EARNINGS_RELEASE
        
        if any(x in title_lower for x in ['research', 'analysis', 'study']):
            return WebSourceType.RESEARCH_PAPER
        
        if any(x in title_lower for x in ['press release', 'announcement']):
            return WebSourceType.PRESS_RELEASE
        
        if any(x in title_lower for x in ['market', 'outlook', 'commentary', 'review']):
            return WebSourceType.MARKET_COMMENTARY
        
        if any(x in title_lower for x in ['deep dive', 'in-depth', 'comprehensive']):
            return WebSourceType.DEEP_DIVE
        
        # Default to news article
        return WebSourceType.NEWS_ARTICLE
    
    # =========================================================================
    # INGESTION PIPELINE
    # =========================================================================
    
    def ingest_url(
        self,
        url: str,
        source_type: Optional[WebSourceType] = None,
        sector_category: Optional[SectorCategory] = None,
        subcategory: Optional[str] = None,
        published_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Ingest content from a URL into documents table.
        
        Args:
            url: URL to fetch
            source_type: Override auto-classification
            sector_category: Economic sector (optional)
            subcategory: Specific subcategory (optional)
            published_at: Publication date (optional)
            metadata: Additional metadata
            
        Returns:
            List of created Document objects
        """
        # Fetch content
        if url.lower().endswith('.pdf'):
            title, content = self.fetch_pdf(url)
        else:
            title, content = self.fetch_url(url)
        
        # Classify source type if not provided
        if source_type is None:
            source_type = self.classify_source_type(url, title, content)
        
        # Chunk content
        chunks = self.chunk_text(content)
        
        documents = []
        
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = self.embedding_service.embed_document(
                title=title,
                content=chunk
            )
            
            # Create document (without embedding - stored separately in Qdrant)
            doc = Document(
                source_type=source_type,
                sector_category=sector_category,
                subcategory=subcategory,
                title=f"{title} (Part {i+1}/{len(chunks)})" if len(chunks) > 1 else title,
                content=chunk,
                url=url,
                published_at=published_at,
                metadata=metadata or {}
            )
            
            # Store embedding separately for Qdrant
            documents.append((doc, embedding))
        
        # Store in database
        self._store_documents(documents)
        
        return documents
    
    def ingest_pdf(
        self,
        pdf_path: str,
        source_type: Optional[WebSourceType] = None,
        sector_category: Optional[SectorCategory] = None,
        subcategory: Optional[str] = None,
        published_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Ingest content from a local PDF file.
        
        Args:
            pdf_path: Path to PDF file
            source_type: Source type (defaults to INDUSTRY_REPORT)
            sector_category: Economic sector (optional)
            subcategory: Specific subcategory (optional)
            published_at: Publication date (optional)
            metadata: Additional metadata
            
        Returns:
            List of created Document objects
        """
        title, content = self.fetch_pdf(pdf_path)
        
        # Default to industry report for PDFs
        if source_type is None:
            source_type = WebSourceType.INDUSTRY_REPORT
        
        # Chunk content
        chunks = self.chunk_text(content)
        
        documents = []
        
        for i, chunk in enumerate(chunks):
            embedding = self.embedding_service.embed_document(
                title=title,
                content=chunk
            )
            
            doc = Document(
                source_type=source_type,
                sector_category=sector_category,
                subcategory=subcategory,
                title=f"{title} (Part {i+1}/{len(chunks)})" if len(chunks) > 1 else title,
                content=chunk,
                source_filename=pdf_path,
                published_at=published_at,
                metadata=metadata or {}
            )
            
            # Store embedding separately for Qdrant
            documents.append((doc, embedding))
        
        self._store_documents(documents)
        
        return documents
    
    def ingest_text(
        self,
        title: str,
        content: str,
        source_type: WebSourceType,
        sector_category: Optional[SectorCategory] = None,
        subcategory: Optional[str] = None,
        url: Optional[str] = None,
        published_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Ingest raw text content.
        
        Args:
            title: Document title
            content: Raw text content
            source_type: Source type (required)
            sector_category: Economic sector (optional)
            subcategory: Specific subcategory (optional)
            url: Source URL if applicable
            published_at: Publication date
            metadata: Additional metadata
            
        Returns:
            List of created Document objects
        """
        chunks = self.chunk_text(content)
        documents = []
        
        for i, chunk in enumerate(chunks):
            embedding = self.embedding_service.embed_document(
                title=title,
                content=chunk
            )
            
            doc = Document(
                source_type=source_type,
                sector_category=sector_category,
                subcategory=subcategory,
                title=f"{title} (Part {i+1}/{len(chunks)})" if len(chunks) > 1 else title,
                content=chunk,
                url=url,
                published_at=published_at,
                metadata=metadata or {}
            )
            
            # Store embedding separately for Qdrant
            documents.append((doc, embedding))
        
        self._store_documents(documents)
        
        return documents
    
    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================
    
    def _store_documents(self, documents: List[tuple]) -> None:
        """
        Store documents in Supabase and embeddings in Qdrant.
        UUID from Supabase is used as the vector ID in Qdrant.
        """
        for doc, embedding in documents:
            # Store document in Supabase (returns UUID)
            data = doc.to_db_dict()
            result = self.supabase.table("documents").insert(data).execute()
            
            # Get the UUID from Supabase response
            doc_id = result.data[0]['id']
            
            # Store embedding in Qdrant with same UUID
            self.qdrant.upsert_vector(
                doc_id=doc_id,
                embedding=embedding,
                sector_category=doc.sector_category.value if doc.sector_category else None,
                source_type=doc.source_type.value,
                subcategory=doc.subcategory
            )
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
