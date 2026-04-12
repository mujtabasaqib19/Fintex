"""
Embedding service using Ollama's nomic-embed-text model.
"""
from typing import List, Optional
import httpx
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import get_settings


class EmbeddingService:
    """Service for generating text embeddings using Ollama."""
    
    def __init__(self, base_url: str = None, model: str = None):
        """
        Initialize Ollama embedding service.
        
        Args:
            base_url: Ollama server URL (reads from OLLAMA_BASE_URL env var if not provided)
            model: Embedding model name (reads from OLLAMA_EMBEDDING_MODEL env var if not provided)
        """
        settings = get_settings()
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_embedding_model
        self.client = httpx.Client(timeout=60.0)
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector (768 dimensions for nomic-embed-text)
        """
        response = self.client.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": self.model,
                "prompt": text
            }
        )
        response.raise_for_status()
        result = response.json()
        return result['embedding']
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query.
        
        Args:
            query: Query text to embed
            
        Returns:
            Embedding vector optimized for retrieval
        """
        # For nomic-embed-text, we can optionally prefix with "search_query: "
        # but the model handles it well without
        return self.embed_text(query)
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = self.embed_text(text)
            embeddings.append(embedding)
        return embeddings
    
    def embed_document(self, title: str, content: str) -> List[float]:
        """
        Generate embedding for a document using title + content.
        
        Args:
            title: Document title
            content: Document content
            
        Returns:
            Embedding vector
        """
        # Prefix with "search_document: " for better retrieval performance
        combined_text = f"search_document: {title}\n\n{content}"
        return self.embed_text(combined_text)
    
    def __del__(self):
        """Close HTTP client on cleanup."""
        if hasattr(self, 'client'):
            self.client.close()
