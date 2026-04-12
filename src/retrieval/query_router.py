"""
Query Router for determining retrieval strategy.
Decides whether to use documents, time-series, or both.
"""
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import google.generativeai as genai
import json
import re
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.categories import SectorCategory, get_sector_categories
from config.settings import get_settings


class QueryIntent(str, Enum):
    """Classification of query intent."""
    NARRATIVE = "narrative"  # Needs explanation, context, news
    NUMERIC = "numeric"      # Needs data, trends, values
    HYBRID = "hybrid"        # Needs both
    UNKNOWN = "unknown"


class QueryRouter:
    """
    Routes user queries to appropriate retrieval systems.
    
    Determines:
    1. Query intent (narrative/numeric/hybrid)
    2. Sector category filter
    3. Time range if applicable
    4. Specific entities/symbols mentioned
    """
    
    # Keywords indicating narrative/document needs
    NARRATIVE_KEYWORDS = [
        'why', 'explain', 'what happened', 'news', 'analysis',
        'opinion', 'outlook', 'forecast', 'report', 'article',
        'announce', 'statement', 'policy', 'decision', 'impact',
        'cause', 'reason', 'factor', 'driver', 'implication'
    ]
    
    # Keywords indicating numeric/time-series needs
    NUMERIC_KEYWORDS = [
        'price', 'rate', 'value', 'trend', 'chart', 'graph',
        'historical', 'data', 'performance', 'return', 'growth',
        'decline', 'increase', 'decrease', 'high', 'low',
        'average', 'compare', 'correlation', 'volatility'
    ]
    
    def __init__(self):
        self.settings = get_settings()
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel(self.settings.chat_model)
    
    # =========================================================================
    # INTENT CLASSIFICATION
    # =========================================================================
    
    def classify_intent(self, query: str) -> QueryIntent:
        """
        Classify query intent using keyword matching.
        
        Args:
            query: User query string
            
        Returns:
            QueryIntent enum value
        """
        query_lower = query.lower()
        
        narrative_score = sum(1 for kw in self.NARRATIVE_KEYWORDS if kw in query_lower)
        numeric_score = sum(1 for kw in self.NUMERIC_KEYWORDS if kw in query_lower)
        
        if narrative_score > 0 and numeric_score > 0:
            return QueryIntent.HYBRID
        elif narrative_score > numeric_score:
            return QueryIntent.NARRATIVE
        elif numeric_score > narrative_score:
            return QueryIntent.NUMERIC
        else:
            return QueryIntent.HYBRID  # Default to hybrid for safety
    
    def _clean_json(self, text: str) -> str:
        """Helper to extract JSON from markdown code blocks if needed."""
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        return text.strip()

    def classify_intent_llm(self, query: str) -> Dict[str, Any]:
        """
        Classify query intent using LLM for complex queries.
        Falls back to local analysis if quota is exceeded or error occurs.
        """
        prompt = f"""Analyze this user query and determine what information is needed:

Query: "{query}"

Respond ONLY with a JSON object:
{{
    "intent": "narrative" | "numeric" | "hybrid",
    "needs_documents": true,
    "needs_timeseries": true,
    "sector_category": "stocks" | "macro" | "banking" | null,
    "entities": ["FFBL", "USD", etc],
    "time_range": {{
        "mentioned": true,
        "start": "2021-01-01",
        "end": "2021-12-31"
    }}
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            clean_text = self._clean_json(response.text)
            return json.loads(clean_text)
        except Exception as e:
            # Check for specifically 429 or quota issues
            print(f"LLM routing error (falling back to regex): {e}")
            
            # Create a fallback dictionary using our local regex extractors
            start, end = self.extract_time_range(query)
            entities = self.extract_entities(query)
            sector = self.detect_sector(query)
            intent = self.classify_intent(query)
            
            return {
                "intent": intent.value if hasattr(intent, 'value') else "hybrid",
                "needs_documents": True,
                "needs_timeseries": True,
                "sector_category": sector.value if hasattr(sector, 'value') else sector,
                "entities": entities,
                "time_range": {
                    "mentioned": start is not None,
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                }
            }
    
    # =========================================================================
    # SECTOR DETECTION
    # =========================================================================
    
    def detect_sector(self, query: str) -> Optional[SectorCategory]:
        """
        Detect sector category from query.
        
        Args:
            query: User query string
            
        Returns:
            SectorCategory if detected, else None
        """
        query_lower = query.lower()
        
        # Direct sector mentions
        sector_keywords = {
            SectorCategory.BANKING: ['bank', 'kibor', 'sbp', 'lending', 'deposit'],
            SectorCategory.BONDS: ['bond', 'pib', 't-bill', 'sukuk'],
            SectorCategory.COMMODITIES: ['cement', 'coal', 'oil', 'gold', 'commodity', 'commodities'],
            SectorCategory.CORPORATE_ACTIONS: ['dividend', 'merger', 'acquisition', 'ipo'],
            SectorCategory.CURRENCY_FX: ['dollar', 'rupee', 'forex', 'exchange rate', 'usd', 'pkr'],
            SectorCategory.DERIVATIVES: ['futures', 'options', 'derivative'],
            SectorCategory.ECONOMIC_INDICATORS: ['gdp', 'inflation', 'cpi', 'trade balance', 'deficit'],
            SectorCategory.FUNDS_ETFS: ['mutual fund', 'etf', 'nav'],
            SectorCategory.INSURANCE: ['insurance', 'premium', 'claim'],
            SectorCategory.REAL_ESTATE: ['property', 'real estate', 'housing', 'construction'],
            SectorCategory.STOCKS: ['stock', 'share', 'psx', 'kse', 'equity'],
        }
        
        for sector, keywords in sector_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return sector
        
        return None
    
    # =========================================================================
    # TIME RANGE EXTRACTION
    # =========================================================================
    
    def extract_time_range(
        self, 
        query: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Extract time range from query.
        
        Args:
            query: User query string
            
        Returns:
            Tuple of (start_date, end_date)
        """
        query_lower = query.lower()
        now = datetime.utcnow()
        
        # Relative time patterns
        relative_patterns = {
            r'last (\d+) days?': lambda m: (now - timedelta(days=int(m.group(1))), now),
            r'last (\d+) weeks?': lambda m: (now - timedelta(weeks=int(m.group(1))), now),
            r'last (\d+) months?': lambda m: (now - timedelta(days=int(m.group(1)) * 30), now),
            r'past week': lambda m: (now - timedelta(weeks=1), now),
            r'past month': lambda m: (now - timedelta(days=30), now),
            r'this week': lambda m: (now - timedelta(days=now.weekday()), now),
            r'this month': lambda m: (now.replace(day=1), now),
            r'today': lambda m: (now.replace(hour=0, minute=0, second=0), now),
            r'yesterday': lambda m: (now - timedelta(days=1), now - timedelta(days=1)),
            r'ytd|year to date': lambda m: (now.replace(month=1, day=1), now),
        }
        
        # Try to extract year-only patterns (e.g., "2021" or "2011 to 2015")
        year_matches = re.findall(r'\b(20\d{2})\b', query)
        if len(year_matches) >= 2:
            try:
                start = datetime(int(year_matches[0]), 1, 1)
                end = datetime(int(year_matches[1]), 12, 31)
                return (start, end)
            except: pass
        elif len(year_matches) == 1:
            try:
                start = datetime(int(year_matches[0]), 1, 1)
                end = datetime(int(year_matches[0]), 12, 31)
                return (start, end)
            except: pass

        # Existing datetime patterns
        for pattern, extractor in relative_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                return extractor(match)
        
        # Try to extract specific dates (YYYY-MM-DD or similar)
        date_pattern = r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})'
        dates = re.findall(date_pattern, query)
        
        if len(dates) >= 2:
            try:
                start = datetime.strptime(dates[0].replace('/', '-'), '%Y-%m-%d')
                end = datetime.strptime(dates[1].replace('/', '-'), '%Y-%m-%d')
                return (start, end)
            except: pass
        elif len(dates) == 1:
            try:
                dt = datetime.strptime(dates[0].replace('/', '-'), '%Y-%m-%d')
                return (dt, now)
            except: pass
        
        return (None, None)
    
    # =========================================================================
    # ENTITY EXTRACTION
    # =========================================================================
    
    def extract_entities(self, query: str) -> List[str]:
        """
        Extract mentioned entities (symbols, companies, indicators).
        
        Args:
            query: User query string
            
        Returns:
            List of entity strings
        """
        entities = []
        
        # Stock symbols (case-insensitive 3-5 letters, e.g., FFBL, ffbl, MEBL)
        # Avoid common words by ignoring common 3-letter English words if needed
        symbols = re.findall(r'\b([a-zA-Z]{3,5})\b', query)
        # Filter: strictly uppercase or known symbols if preferred, but for now we'll take all
        entities.extend([s.upper() for s in symbols if s.lower() not in ['the', 'and', 'for', 'was', 'are', 'not']])
        
        # Currency pairs
        pairs = re.findall(r'\b(USD|EUR|GBP|PKR|AED)[/_-](PKR|USD|EUR|GBP)\b', query, re.I)
        entities.extend([f"{p[0]}_{p[1]}".upper() for p in pairs])
        
        # Known indices
        indices = ['KSE-100', 'KSE100', 'KSE-30', 'KMI-30']
        for idx in indices:
            if idx.lower() in query.lower():
                entities.append(idx.replace('-', ''))
        
        return list(set(entities))
    
    # =========================================================================
    # MAIN ROUTING
    # =========================================================================
    
    def route(self, query: str, use_llm: bool = False) -> Dict[str, Any]:
        """
        Analyze query and determine retrieval strategy.
        
        Args:
            query: User query string
            use_llm: Whether to use LLM for complex analysis
            
        Returns:
            Routing decision dict
        """
        if use_llm:
            llm_analysis = self.classify_intent_llm(query)
            intent = QueryIntent(llm_analysis.get("intent", "hybrid"))
            sector_value = llm_analysis.get("sector_category")
            sector = SectorCategory(sector_value) if sector_value in get_sector_categories() else None
            entities = llm_analysis.get("entities", [])
            
            time_info = llm_analysis.get("time_range", {})
            if time_info.get("start"):
                start = datetime.fromisoformat(time_info["start"])
            elif time_info.get("relative"):
                start, _ = self.extract_time_range(time_info["relative"])
            else:
                start = None
            
            end = datetime.fromisoformat(time_info["end"]) if time_info.get("end") else None
            
        else:
            intent = self.classify_intent(query)
            sector = self.detect_sector(query)
            entities = self.extract_entities(query)
            start, end = self.extract_time_range(query)
        
        # Determine retrieval needs
        needs_documents = intent in [QueryIntent.NARRATIVE, QueryIntent.HYBRID]
        needs_timeseries = intent in [QueryIntent.NUMERIC, QueryIntent.HYBRID]
        
        return {
            "query": query,
            "intent": intent.value,
            "needs_documents": needs_documents,
            "needs_timeseries": needs_timeseries,
            "sector_category": sector.value if sector else None,
            "entities": entities,
            "time_range": {
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
            },
            "retrieval_priority": "documents" if intent == QueryIntent.NARRATIVE else 
                                 "timeseries" if intent == QueryIntent.NUMERIC else 
                                 "balanced"
        }
