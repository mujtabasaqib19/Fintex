"""
Sector Classifier for assigning economic domain categories using Gemini.
Connects content to the fixed 11 sector categories.
"""
from typing import Optional, Tuple, Dict, List, Any
import google.generativeai as genai
import json
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.categories import (
    SectorCategory, normalize_subcategory, 
    get_sector_categories, SUBCATEGORY_EXAMPLES
)
from config.settings import get_settings


class SectorClassifier:
    """
    Classifier for assigning sector categories to content.
    
    Rules:
    - sector_category MUST be one of the 11 fixed categories
    - subcategory can be dynamic but must be normalized
    - This classifier is used for BOTH web docs and time-series
    """
    
    SECTOR_DESCRIPTIONS = {
        SectorCategory.BANKING: "Banking sector - banks, lending, deposits, KIBOR, SBP rates, monetary policy",
        SectorCategory.BONDS: "Bonds & fixed income - PIBs, T-bills, sukuk, ijara, government securities",
        SectorCategory.COMMODITIES: "Commodities - cement, coal, cotton, crude oil, gold, silver, wheat, rice, sugar, metals",
        SectorCategory.CORPORATE_ACTIONS: "Corporate actions - dividends, stock splits, rights issues, mergers, acquisitions",
        SectorCategory.CURRENCY_FX: "Currency & forex - USD/PKR, EUR/PKR, exchange rates, remittances, forex reserves",
        SectorCategory.DERIVATIVES: "Derivatives - futures, options, swaps, hedging instruments",
        SectorCategory.ECONOMIC_INDICATORS: "Economic indicators - GDP, CPI, inflation, trade balance, fiscal deficit, current account",
        SectorCategory.FUNDS_ETFS: "Funds & ETFs - mutual funds, ETFs, NAV, AUM, fund performance",
        SectorCategory.INSURANCE: "Insurance sector - life, general, reinsurance, claims, premiums",
        SectorCategory.REAL_ESTATE: "Real estate - property, construction, housing, REITs, land prices",
        SectorCategory.STOCKS: "Stocks & equities - PSX, KSE-100, stock prices, market cap, trading volume",
    }
    
    def __init__(self):
        self.settings = get_settings()
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel(self.settings.chat_model)
        self._build_keyword_map()
    
    def _build_keyword_map(self) -> None:
        """Build keyword-to-sector mapping for fast classification."""
        self.keyword_map: Dict[str, SectorCategory] = {}
        
        # Banking keywords
        for kw in ['bank', 'kibor', 'sbp', 'lending', 'deposit', 'monetary', 'policy rate']:
            self.keyword_map[kw] = SectorCategory.BANKING
        
        # Bonds keywords
        for kw in ['pib', 't-bill', 'tbill', 'sukuk', 'ijara', 'bond', 'fixed income', 'government securities']:
            self.keyword_map[kw] = SectorCategory.BONDS
        
        # Commodities keywords
        for kw in ['cement', 'coal', 'cotton', 'crude', 'oil', 'gold', 'silver', 'wheat', 'rice', 
                   'sugar', 'commodity', 'commodities', 'brent', 'wti', 'clinker']:
            self.keyword_map[kw] = SectorCategory.COMMODITIES
        
        # Corporate actions keywords
        for kw in ['dividend', 'split', 'rights issue', 'merger', 'acquisition', 'buyback', 'ipo']:
            self.keyword_map[kw] = SectorCategory.CORPORATE_ACTIONS
        
        # Currency/FX keywords
        for kw in ['forex', 'fx', 'exchange rate', 'usd', 'pkr', 'eur', 'gbp', 'remittance', 
                   'currency', 'dollar', 'rupee']:
            self.keyword_map[kw] = SectorCategory.CURRENCY_FX
        
        # Derivatives keywords
        for kw in ['futures', 'options', 'swap', 'derivative', 'hedge', 'forward']:
            self.keyword_map[kw] = SectorCategory.DERIVATIVES
        
        # Economic indicators keywords
        for kw in ['gdp', 'cpi', 'inflation', 'trade balance', 'deficit', 'current account',
                   'fiscal', 'exports', 'imports', 'growth rate']:
            self.keyword_map[kw] = SectorCategory.ECONOMIC_INDICATORS
        
        # Funds/ETFs keywords
        for kw in ['mutual fund', 'etf', 'nav', 'aum', 'fund manager', 'asset allocation']:
            self.keyword_map[kw] = SectorCategory.FUNDS_ETFS
        
        # Insurance keywords
        for kw in ['insurance', 'premium', 'claim', 'underwriting', 'reinsurance', 'life insurance']:
            self.keyword_map[kw] = SectorCategory.INSURANCE
        
        # Real estate keywords
        for kw in ['real estate', 'property', 'housing', 'construction', 'reit', 'land', 'plaza']:
            self.keyword_map[kw] = SectorCategory.REAL_ESTATE
        
        # Stocks keywords
        for kw in ['psx', 'kse', 'stock', 'share', 'equity', 'trading', 'market cap', 'bull', 'bear']:
            self.keyword_map[kw] = SectorCategory.STOCKS
    
    def classify_by_keywords(
        self, 
        text: str
    ) -> Optional[SectorCategory]:
        """Fast classification using keyword matching."""
        text_lower = text.lower()
        
        # Count matches per sector
        sector_scores: Dict[SectorCategory, int] = {}
        
        for keyword, sector in self.keyword_map.items():
            if keyword in text_lower:
                sector_scores[sector] = sector_scores.get(sector, 0) + 1
        
        if not sector_scores:
            return None
        
        # Return highest scoring sector
        sorted_sectors = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_sectors) == 1:
            return sorted_sectors[0][0]
        
        # Need clear winner (at least 2x second place)
        if sorted_sectors[0][1] >= sorted_sectors[1][1] * 2:
            return sorted_sectors[0][0]
        
        return None
    
    def classify_by_llm(
        self, 
        title: str, 
        content: str
    ) -> Tuple[Optional[SectorCategory], Optional[str]]:
        """Classify content using Gemini LLM."""
        sector_list = "\n".join([
            f"- {cat.value}: {desc}" 
            for cat, desc in self.SECTOR_DESCRIPTIONS.items()
        ])
        
        prompt = f"""Classify the following content into ONE of these economic sectors:

{sector_list}

Content Title: {title}
Content: {content[:2000]}

Respond with a JSON object:
{{
    "sector_category": "<one of the sector values exactly as listed above>",
    "subcategory": "<specific topic in snake_case, e.g., cement, kse100, usd_pkr>",
    "confidence": <0.0 to 1.0>,
    "reasoning": "<brief explanation>"
}}

RULES:
1. sector_category MUST be exactly one of: {', '.join(get_sector_categories())}
2. subcategory should be a specific, normalized snake_case string
3. If content spans multiple sectors, choose the PRIMARY one
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            
            sector_value = result.get("sector_category")
            subcategory = result.get("subcategory")
            
            # Validate sector category
            if sector_value not in get_sector_categories():
                return None, None
            
            sector = SectorCategory(sector_value)
            normalized_sub = normalize_subcategory(subcategory) if subcategory else None
            
            return sector, normalized_sub
        except Exception as e:
            print(f"LLM classification error: {e}")
            return None, None
    
    def classify(
        self, 
        title: str, 
        content: str,
        use_llm: bool = True
    ) -> Tuple[Optional[SectorCategory], Optional[str]]:
        """Classify content using hybrid approach."""
        combined = f"{title} {content}"
        
        # Try keyword match first
        sector = self.classify_by_keywords(combined)
        
        if sector:
            # Extract subcategory using simple heuristics
            subcategory = self._extract_subcategory(combined, sector)
            return sector, subcategory
        
        # Fall back to LLM if enabled
        if use_llm:
            return self.classify_by_llm(title, content)
        
        return None, None
    
    def _extract_subcategory(
        self, 
        text: str, 
        sector: SectorCategory
    ) -> Optional[str]:
        """Extract subcategory from text based on sector."""
        text_lower = text.lower()
        
        # Check known subcategories for this sector
        known_subs = SUBCATEGORY_EXAMPLES.get(sector, [])
        for sub in known_subs:
            if sub in text_lower or sub.replace('_', ' ') in text_lower:
                return sub
        
        # Extract potential subcategory using patterns
        if sector == SectorCategory.STOCKS:
            symbols = re.findall(r'\b([A-Z]{2,5})\b', text)
            if symbols:
                return symbols[0].lower()
        
        elif sector == SectorCategory.CURRENCY_FX:
            pairs = re.findall(r'\b(USD|EUR|GBP|PKR|AED)[/_-](PKR|USD|EUR|GBP)\b', text, re.I)
            if pairs:
                return f"{pairs[0][0]}_{pairs[0][1]}".lower()
        
        return None
    
    def classify_series(
        self, 
        symbol: str, 
        metric: str, 
        provider: str
    ) -> Tuple[Optional[SectorCategory], Optional[str]]:
        """Classify a time-series based on its metadata."""
        provider_lower = provider.lower()
        
        if provider_lower == 'psx':
            return SectorCategory.STOCKS, symbol.lower()
        
        if provider_lower == 'sbp':
            if 'kibor' in symbol.lower():
                return SectorCategory.BANKING, 'kibor'
            return SectorCategory.BANKING, normalize_subcategory(symbol)
        
        if provider_lower == 'forex':
            return SectorCategory.CURRENCY_FX, normalize_subcategory(symbol)
        
        # Symbol-based classification
        combined = f"{symbol} {metric} {provider}"
        sector = self.classify_by_keywords(combined)
        if sector:
            return sector, normalize_subcategory(symbol)
        
        return None, normalize_subcategory(symbol)
