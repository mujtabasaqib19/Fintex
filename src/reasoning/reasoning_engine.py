"""
Reasoning Engine using Tree of Thought (ToT) with Gemini.
Decomposes complex queries and gathers evidence.
"""
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import json
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import get_settings
from config.categories import SectorCategory
from src.retrieval import QueryRouter, DocumentRetriever, TimeSeriesRetriever, PakistanStockRetriever, LiveWebRetriever


class ReasoningEngine:
    """
    Tree of Thought reasoning engine for complex query analysis.
    
    Process:
    1. Decompose query into sub-questions
    2. Route each sub-question appropriately
    3. Gather evidence from documents and time-series
    4. Synthesize findings
    """
    
    def __init__(self):
        self.settings = get_settings()
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel(self.settings.chat_model)
        
        self.router = QueryRouter()
        self.doc_retriever = DocumentRetriever()
        self.ts_retriever = TimeSeriesRetriever()
        self.stock_retriever = PakistanStockRetriever()  # Agent 3: Pakistan Stocks
        self.web_retriever = LiveWebRetriever()  # Agent 1 extension: Live Web
    
    def reason(self, query: str) -> Dict[str, Any]:
        """
        Full Tree of Thought reasoning pipeline.
        
        Args:
            query: User's question
            
        Returns:
            Dict with decomposed questions, evidence, and analysis
        """
        # Step 1: Decompose query
        decomposition = self._decompose_query(query)
        
        # Step 2: Gather evidence for each sub-question
        evidence = self._gather_evidence(decomposition)
        
        # Step 3: Return structured reasoning result
        return {
            "original_query": query,
            "decomposition": decomposition,
            "evidence": evidence,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def reason_simple(self, query: str) -> Dict[str, Any]:
        """
        Simplified reasoning without full ToT decomposition.
        
        Args:
            query: User's question
            
        Returns:
            Dict with evidence
        """
        # Route the query
        routing = self.router.route(query, use_llm=False)
        
        evidence = {
            "routing": routing,
            "document_evidence": [],
            "timeseries_evidence": [],
            "stock_market_evidence": []  # New: Pakistani stocks
        }
        
        # Gather documents if needed
        if routing["needs_documents"]:
            sector = SectorCategory(routing["sector_category"]) if routing["sector_category"] else None
            # Get from internal database
            docs = self.doc_retriever.search(
                query=query,
                limit=5,
                sector_category=sector
            )
            
            # Supplement with live web data
            # Determine if this needs news vs general web info based on intent/temporal
            if routing.get("intent") == "narrative" or routing.get("time_range", {}).get("start") is not None:
                web_docs = self.web_retriever.search_news(query, limit=3)
            else:
                web_docs = self.web_retriever.search_general(query, limit=2)
                
            evidence["document_evidence"] = web_docs + docs
        
        # Check if this is a stock market query (Agent 3)
        is_stock_query = (
            routing.get("sector_category") == "stocks" or
            any(word in query.lower() for word in ['stock', 'share', 'psx', 'kse', 'price', 'akbltfc6'])
        )
        
        if is_stock_query:
            # Extract potential stock symbols from entities
            symbols = []
            for entity in routing.get("entities", []):
                # Check if entity looks like a stock symbol (uppercase letters)
                if entity.isupper() and len(entity) >= 3:
                    symbols.append(entity)
            
            # If no symbols found, try some common ones or use market snapshot
            if not symbols:
                # Get market snapshot
                snapshot = self.stock_retriever.get_market_snapshot(limit=5)
                for stock in snapshot:
                    evidence["stock_market_evidence"].append({
                        "type": "market_snapshot",
                        "data": stock,
                        "formatted": self.stock_retriever.format_price_for_context(stock)
                    })
            else:
                # Get data for specific symbols
                for symbol in symbols[:5]:  # Limit to 5 symbols
                    # Get latest price
                    latest = self.stock_retriever.get_latest_price(symbol)
                    if latest:
                        evidence["stock_market_evidence"].append({
                            "type": "latest_price",
                            "symbol": symbol,
                            "data": latest,
                            "formatted": self.stock_retriever.format_price_for_context(latest)
                        })
                    
                    # Get statistics
                    stats = self.stock_retriever.get_price_stats(symbol, days=30)
                    if stats:
                        evidence["stock_market_evidence"].append({
                            "type": "statistics",
                            "symbol": symbol,
                            "data": stats,
                            "formatted": self.stock_retriever.format_stats_for_context(stats)
                        })
        
        # Gather time-series if needed
        if routing["needs_timeseries"] and routing["entities"]:
            for entity in routing["entities"]:
                # Try to find series matching this entity
                sector = SectorCategory(routing["sector_category"]) if routing["sector_category"] else None
                if sector:
                    summary = self.ts_retriever.get_sector_summary(sector, limit=5)
                    evidence["timeseries_evidence"].extend(summary)
        
        return evidence
    
    def _decompose_query(self, query: str) -> Dict[str, Any]:
        """
        Decompose a complex query into sub-questions using Gemini.
        
        Args:
            query: Original user query
            
        Returns:
            Dict with sub-questions and their types
        """
        prompt = f"""You are a financial analyst breaking down user questions into sub-questions.

User Query: "{query}"

Decompose this into 2-4 focused sub-questions that together answer the original query.
For each sub-question, classify it as:
- "factual": Needs current data/facts
- "analytical": Needs analysis/explanation
- "comparative": Needs comparison between items
- "temporal": Needs historical trends

Respond with JSON:
{{
    "sub_questions": [
        {{
            "question": "What is the current value of X?",
            "type": "factual",
            "needs_documents": true/false,
            "needs_timeseries": true/false
        }},
        ...
    ],
    "reasoning": "Brief explanation of decomposition strategy"
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # Fallback if not proper JSON
            return {
                "sub_questions": [
                    {
                        "question": query,
                        "type": "factual",
                        "needs_documents": True,
                        "needs_timeseries": True
                    }
                ],
                "reasoning": "Fallback to single question"
            }
        except Exception as e:
            print(f"Decomposition error: {e}")
            # Fallback to simple decomposition
            return {
                "sub_questions": [
                    {
                        "question": query,
                        "type": "factual",
                        "needs_documents": True,
                        "needs_timeseries": True
                    }
                ],
                "reasoning": "Fallback to single question"
            }
    
    def _gather_evidence(self, decomposition: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Gather evidence for each sub-question.
        
        Args:
            decomposition: Output from _decompose_query
            
        Returns:
            List of evidence dicts for each sub-question
        """
        evidence_list = []
        
        for sub_q in decomposition.get("sub_questions", []):
            question = sub_q["question"]
            
            evidence = {
                "sub_question": question,
                "type": sub_q["type"],
                "documents": [],
                "timeseries": []
            }
            
            # Gather documents if needed
            if sub_q.get("needs_documents", True):
                try:
                    docs = self.doc_retriever.search(
                        query=question,
                        limit=3
                    )
                    
                    if sub_q.get("type") == "temporal" or "news" in question.lower() or "latest" in question.lower():
                        web_docs = self.web_retriever.search_news(question, limit=2)
                    else:
                        web_docs = self.web_retriever.search_general(question, limit=1)
                        
                    evidence["documents"] = web_docs + docs
                except Exception as e:
                    print(f"Document/Web retrieval error: {e}")
            
            # Gather time-series if needed
            if sub_q.get("needs_timeseries", False):
                try:
                    # Route to detect entities
                    routing = self.router.route(question)
                    
                    if routing.get("entities"):
                        # Try to get data for mentioned entities
                        for entity in routing["entities"][:2]:  # Limit to 2 entities
                            # Construct likely series_id
                            series_id = entity.lower()
                            latest = self.ts_retriever.get_latest(series_id)
                            if latest:
                                evidence["timeseries"].append(latest)
                except Exception as e:
                    print(f"Time-series retrieval error: {e}")
            
            evidence_list.append(evidence)
        
        return evidence_list
    
    def evaluate_confidence(
        self, 
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate confidence in the gathered evidence.
        
        Args:
            evidence: List of evidence dicts
            
        Returns:
            Confidence assessment
        """
        total_docs = sum(len(e.get("documents", [])) for e in evidence)
        total_ts = sum(len(e.get("timeseries", [])) for e in evidence)
        
        # Simple heuristic
        if total_docs >= 3 or total_ts >= 2:
            level = "high"
        elif total_docs >= 1 or total_ts >= 1:
            level = "medium"
        else:
            level = "low"
        
        return {
            "level": level,
            "document_count": total_docs,
            "timeseries_count": total_ts,
            "reasoning": f"Found {total_docs} documents and {total_ts} time-series data points"
        }
