"""
Live Web Retriever using SerpApi.
Fetches real-time search results (News, Finance) to supplement the internal database.
"""
from typing import List, Dict, Any, Optional
import sys
import os

try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import get_settings


class LiveWebRetriever:
    """
    Retriever for finding real-time information from the web.
    Uses SerpApi to search Google News and regular Search.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.serpapi_api_key
        self.enabled = self.api_key is not None and GoogleSearch is not None
        
        if not self.enabled:
            print("Warning: LiveWebRetriever is disabled. Please install google-search-results and set SERPAPI_API_KEY in .env")
            
    def search_news(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search Google News for real-time information.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching news articles formatted like DocumentRetriever results
        """
        if not self.enabled:
            return []
            
        params = {
            "engine": "google",
            "q": query,
            "tbm": "nws",  # News search
            "gl": "pk",    # Country: Pakistan
            "api_key": self.api_key,
            "num": limit
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            news_results = results.get("news_results", [])
            formatted_results = []
            
            for i, article in enumerate(news_results[:limit]):
                title = article.get("title", "Untitled")
                link = article.get("link", "")
                snippet = article.get("snippet", "")
                source = article.get("source", "Web")
                date = article.get("date", "")
                
                formatted_results.append({
                    "id": f"web_{i}",
                    "title": f"{title} [{source}]",
                    "content": f"{date}: {snippet}",
                    "url": link,
                    "source_type": "Live Web Search",
                    "sector_category": "News",
                    "similarity": 1.0  # Assumed high relevance since it matches keyword
                })
                
            return formatted_results
        except Exception as e:
            print(f"SerpApi error: {e}")
            return []
            
    def search_general(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search general Google for real-time information.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching web pages formatted like DocumentRetriever results
        """
        if not self.enabled:
            return []
            
        params = {
            "engine": "google",
            "q": query,
            "gl": "pk",    # Country: Pakistan
            "api_key": self.api_key,
            "num": limit
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            organic_results = results.get("organic_results", [])
            formatted_results = []
            
            for i, result in enumerate(organic_results[:limit]):
                title = result.get("title", "Untitled")
                link = result.get("link", "")
                snippet = result.get("snippet", "")
                source = result.get("source", "Web")
                
                formatted_results.append({
                    "id": f"web_org_{i}",
                    "title": title,
                    "content": snippet,
                    "url": link,
                    "source_type": "Live Web Search",
                    "sector_category": "General",
                    "similarity": 1.0
                })
                
            return formatted_results
        except Exception as e:
            print(f"SerpApi error: {e}")
            return []
