"""
Answer Synthesizer using Gemini.
Generates final answers from gathered evidence.
"""
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import get_settings


class AnswerSynthesizer:
    """
    Synthesizes final answers from evidence using Gemini.
    
    Takes evidence from ReasoningEngine and generates user-friendly responses.
    """
    
    def __init__(self):
        self.settings = get_settings()
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel(self.settings.chat_model)
    
    def synthesize(
        self, 
        reasoning_result: Dict[str, Any],
        format: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Synthesize answer from full reasoning result.
        
        Args:
            reasoning_result: Output from ReasoningEngine.reason()
            format: "detailed", "brief", or "bullet"
            
        Returns:
            Dict with answer and metadata
        """
        query = reasoning_result["original_query"]
        evidence = reasoning_result["evidence"]
        
        # Prepare context from evidence
        context = self._format_evidence(evidence)
        
        # Generate answer
        answer_text = self._generate_answer(query, context, format)
        
        # Calculate confidence
        from src.reasoning.reasoning_engine import ReasoningEngine
        engine = ReasoningEngine()
        confidence = engine.evaluate_confidence(evidence)
        
        return {
            "query": query,
            "answer": answer_text,
            "confidence": confidence,
            "sources": self._extract_sources(evidence),
            "format": format
        }
    
    def synthesize_simple(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        timeseries: List[Dict[str, Any]],
        stock_market: Optional[List[Dict[str, Any]]] = None,
        format: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Synthesize answer from simple evidence lists.
        
        Args:
            query: User's question
            documents: List of document dicts
            timeseries: List of time-series dicts
            stock_market: List of stock market dicts (Agent 3)
            format: Answer format
            
        Returns:
            Dict with answer
        """
        # Format evidence
        stock_market = stock_market or []
        context = self._format_simple_evidence(documents, timeseries, stock_market)
        
        # Generate answer
        answer_text = self._generate_answer(query, context, format)
        
        # Simple confidence
        total_evidence = len(documents) + len(timeseries) + len(stock_market)
        if total_evidence >= 3 or len(stock_market) >= 2:
            confidence_level = "high"
        elif total_evidence >= 1:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        return {
            "query": query,
            "answer": answer_text,
            "confidence": {
                "level": confidence_level,
                "document_count": len(documents),
                "timeseries_count": len(timeseries),
                "stock_market_count": len(stock_market)
            },
            "sources": self._extract_simple_sources(documents, timeseries, stock_market)
        }
    
    def _format_evidence(self, evidence: List[Dict[str, Any]]) -> str:
        """Format evidence from reasoning engine into context string."""
        context_parts = []
        
        for idx, ev in enumerate(evidence, 1):
            sub_q = ev.get("sub_question", "")
            context_parts.append(f"## Sub-Question {idx}: {sub_q}\n")
            
            # Add documents
            for doc in ev.get("documents", []):
                title = doc.get("title", "Untitled")
                content = doc.get("content", "")[:300]
                sector = doc.get("sector_category", "")
                similarity = doc.get("similarity", 0)
                
                context_parts.append(f"""
**Document**: {title}
**Sector**: {sector}
**Relevance**: {similarity:.2f}
**Content**: {content}...
""")
            
            # Add time-series
            for ts in ev.get("timeseries", []):
                series_id = ts.get("series_id", "")
                value = ts.get("value", 0)
                unit = ts.get("unit", "")
                timestamp = ts.get("timestamp", "")
                
                context_parts.append(f"""
**Time Series**: {series_id}
**Latest Value**: {value} {unit}
**As of**: {timestamp}
""")
        
        return "\n".join(context_parts)
    
    def _format_simple_evidence(
        self,
        documents: List[Dict[str, Any]],
        timeseries: List[Dict[str, Any]],
        stock_market: List[Dict[str, Any]] = None
    ) -> str:
        """Format simple evidence lists."""
        stock_market = stock_market or []
        context_parts = []
        
        if documents:
            context_parts.append("## Document Evidence\n")
            for doc in documents:
                title = doc.get("title", "Untitled")
                content = doc.get("content", "")[:300]
                sector = doc.get("sector_category", "")
                
                context_parts.append(f"""
**{title}** ({sector})
{content}...
""")
        
        if stock_market:
            context_parts.append("\n## Pakistan Stock Market Data (PSX)\n")
            for stock_ev in stock_market:
                # Use the formatted context that was already generated
                formatted = stock_ev.get("formatted", "")
                if formatted:
                    context_parts.append(formatted + "\n")
        
        if timeseries:
            context_parts.append("\n## Data Points\n")
            for ts in timeseries:
                series_id = ts.get("series_id", "")
                value = ts.get("value", 0)
                unit = ts.get("unit", "")
                
                context_parts.append(f"- {series_id}: {value} {unit}\n")
        
        return "\n".join(context_parts)
    
    def _generate_answer(
        self, 
        query: str, 
        context: str,
        format: str
    ) -> str:
        """Generate answer using Gemini."""
        format_instructions = {
            "detailed": "Provide a comprehensive, well-structured answer with multiple paragraphs.",
            "brief": "Provide a concise answer in 2-3 sentences.",
            "bullet": "Provide answer as bullet points (3-5 points)."
        }
        
        instruction = format_instructions.get(format, format_instructions["detailed"])
        
        prompt = f"""You are a financial analyst answering user questions based on provided evidence.

User Question: "{query}"

Evidence:
{context}

Instructions: {instruction}

Rules:
1. Answer ONLY based on the evidence provided
2. Cite specific sources when making claims
3. If evidence is insufficient, clearly state what's missing
4. Use clear, professional language
5. For numerical data, be precise and include units
6. Mention the sector/category when relevant

Your Answer:
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    def _extract_sources(self, evidence: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract source citations from evidence."""
        sources = []
        
        for ev in evidence:
            for doc in ev.get("documents", []):
                sources.append({
                    "type": "document",
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "sector": doc.get("sector_category", ""),
                    "source_type": doc.get("source_type", "")
                })
            
            for ts in ev.get("timeseries", []):
                sources.append({
                    "type": "timeseries",
                    "series_id": ts.get("series_id", ""),
                    "provider": ts.get("provider", "")
                })
        
        return sources
    
    def _extract_simple_sources(
        self,
        documents: List[Dict[str, Any]],
        timeseries: List[Dict[str, Any]],
        stock_market: List[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Extract sources from simple evidence."""
        stock_market = stock_market or []
        sources = []
        
        for doc in documents:
            sources.append({
                "type": "document",
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "id": doc.get("id", ""),
                "source_type": doc.get("source_type", "")
            })
        
        for stock_ev in stock_market:
            symbol = stock_ev.get("symbol", stock_ev.get("data", {}).get("symbol", ""))
            sources.append({
                "type": "stock_market",
                "symbol": symbol,
                "source": "Pakistan Stock Exchange (PSX)",
                "data_type": stock_ev.get("type", "price_data")
            })
        
        for ts in timeseries:
            sources.append({
                "type": "timeseries",
                "series_id": ts.get("series_id", ""),
                "provider": ts.get("provider", "")
            })
        
        return sources
    
    def format_for_display(self, answer_dict: Dict[str, Any]) -> str:
        """Format answer dict for pretty display."""
        output = []
        
        output.append(f"**Question**: {answer_dict['query']}\n")
        output.append(f"**Answer**: {answer_dict['answer']}\n")
        
        confidence = answer_dict.get("confidence", {})
        output.append(f"**Confidence**: {confidence.get('level', 'unknown').upper()}")
        output.append(f"  - Documents: {confidence.get('document_count', 0)}")
        output.append(f"  - Data Points: {confidence.get('timeseries_count', 0)}\n")
        
        if answer_dict.get("sources"):
            output.append("**Sources**:")
            for idx, source in enumerate(answer_dict["sources"], 1):
                if source["type"] == "document":
                    output.append(f"  {idx}. {source.get('title', 'Untitled')} ({source.get('sector', '')})")
                else:
                    output.append(f"  {idx}. {source.get('series_id', '')} [{source.get('provider', '')}]")
        
        return "\n".join(output)
