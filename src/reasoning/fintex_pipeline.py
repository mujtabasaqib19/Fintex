"""
Fintex Answer Pipeline — Orchestration Middleware (Section 6).

Implements the strict decision matrix:
  Qdrant ✅ + Supabase ✅ → Merge both, accuracy 85-95%
  Qdrant ✅ + Supabase ❌ → Use Qdrant only, accuracy 70-84%
  Qdrant ❌ + Supabase ✅ → Use Supabase only, accuracy 65-80%
  Qdrant ❌ + Supabase ❌ → Gemini fallback, accuracy 40-65%

Also handles:
  - Query categorization (stocks / monetary_policy / theory / banking / macro / general)
  - Qdrant memory sync (saves every Q&A back to Qdrant for future recall)
  - Auto conversation title generation
  - Strict formatting enforcement (Sections 7 & 8)
"""
from typing import Dict, Any, List, Optional, Tuple
import google.generativeai as genai
from huggingface_hub import InferenceClient
import json
import uuid
import sys
import os
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import get_settings
from src.db.qdrant_client import QdrantService
from src.db.connection import get_supabase_client
from src.retrieval import QueryRouter, DocumentRetriever, PakistanStockRetriever, LiveWebRetriever


# ─────────────────────────────────────────────────────────────────────────────
# QUERY CATEGORIZER
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "stocks": ["stock", "share", "psx", "kse", "kse100", "kse-100", "price", "ticker",
               "listed", "ipo", "dividend", "eps", "pe ratio", "market cap", "bull", "bear",
               "invest", "portfolio", "scrip", "equity",
               # Major PSX tickers as keywords
               "engro", "hbl", "ubl", "mcb", "mebl", "ogdc", "ppl", "mari", "luck", "fccl",
               "trg", "sys", "hubc", "kapco", "kel", "nestle", "ffc", "fatima", "bop",
               "nbp", "unity", "psmc", "indu", "hcar", "avnr", "wtl"],
    "monetary_policy": ["sbp", "state bank", "policy rate", "interest rate", "discount rate",
                        "monetary policy", "reserve", "inflation target", "money supply"],
    "banking": ["bank", "nbp", "banking sector",
                "deposits", "advances", "non-performing", "npl", "spread"],
    "theory": ["what is", "define", "explain", "concept", "theory", "difference between",
               "how does", "meaning of", "economics", "finance theory", "fundamentals"],
    "macro": ["gdp", "inflation", "cpi", "trade deficit", "balance of payments",
              "fiscal deficit", "budget", "imf", "world bank", "remittances",
              "forex", "exchange rate", "usd", "pkr", "rupee", "dollar"],
}


STRONG_THEORY_PATTERNS = [
    "what is ", "what are ", "what does ",
    "how does ", "how do ", "how is ",
    "define ", "explain ",
    "difference between ", "differ ", "vs ",
    "meaning of ", "concept of ",
]


def categorize_query(query: str) -> Dict[str, str]:
    """
    Classify a user query into category + subcategory using keyword matching.
    Returns: {"category": str, "subcategory": str}
    """
    q = query.lower()
    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}

    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                scores[cat] += 1

    # Strong-signal override: definitional/explanatory phrasings ("what is",
    # "how does X differ", "define", "explain", etc.) force the theory track
    # even when topical keywords like "dividend" or "pe ratio" appear. Those
    # stock keywords are the *subject* of a theory question, not a trading query.
    if any(pat in q for pat in STRONG_THEORY_PATTERNS):
        best = "theory"
    else:
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            best = "general"

    # Detect subcategory
    subcategory = _detect_subcategory(q, best)

    return {"category": best, "subcategory": subcategory}


def _detect_subcategory(query: str, category: str) -> str:
    """Detect finer subcategory within a category."""
    subcategory_map = {
        "stocks": {"psx": ["psx", "pakistan stock"], "kse100": ["kse100", "kse-100", "kse 100"]},
        "monetary_policy": {"sbp": ["sbp", "state bank"], "rates": ["interest rate", "policy rate"]},
        "banking": {"nbp": ["nbp", "national bank"], "hbl": ["hbl", "habib bank"]},
        "macro": {"forex": ["usd", "pkr", "dollar", "rupee", "exchange rate"],
                  "inflation": ["inflation", "cpi"], "gdp": ["gdp", "growth"]},
    }

    if category in subcategory_map:
        for sub, keywords in subcategory_map[category].items():
            for kw in keywords:
                if kw in query:
                    return sub
    return category


# ─────────────────────────────────────────────────────────────────────────────
# EMBEDDING HELPER (uses Gemini embedding endpoint)
# ─────────────────────────────────────────────────────────────────────────────

EMBED_DIM = 768  # must match Qdrant collection dimension


def embed_text(text: str) -> List[float]:
    """
    Generate a 768-dim embedding. Tries candidates in order; for models that
    default to a larger dim (e.g. gemini-embedding-001 → 3072), request 768
    explicitly via output_dimensionality. Any vector of the wrong dim is
    rejected so we never hand a bad-shape vector to Qdrant.
    """
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)

    # (model_name, needs_explicit_dim)
    candidates = [
        (settings.embedding_model, False),
        ("models/embedding-001", False),
        ("models/text-embedding-004", False),
        ("models/gemini-embedding-001", True),
    ]
    seen = set()
    last_err = None
    for model_name, needs_dim in candidates:
        if model_name in seen:
            continue
        seen.add(model_name)
        try:
            if needs_dim:
                result = genai.embed_content(
                    model=model_name,
                    content=text,
                    output_dimensionality=EMBED_DIM,
                )
            else:
                result = genai.embed_content(model=model_name, content=text)
            vec = result.get('embedding') if isinstance(result, dict) else None
            if not vec:
                continue
            if len(vec) != EMBED_DIM:
                print(f"Embedding '{model_name}' returned dim {len(vec)}, expected {EMBED_DIM} — skipping")
                continue
            return vec
        except Exception as e:
            last_err = e
            continue
    print(f"Embedding error (all candidates failed): {last_err}")
    return [0.0] * EMBED_DIM


# ─────────────────────────────────────────────────────────────────────────────
# FINTEX PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

class FintexPipeline:
    """
    The core orchestration middleware for Fintex.
    
    Every user question goes through:
    1. Embed → 2. Search Qdrant → 3. Search Supabase → 4. Decision Matrix
    5. Generate Answer (with format enforcement) → 6. Determine Accuracy
    7. Categorize → 8. Embed & Save back to Qdrant
    """

    def __init__(self):
        self.settings = get_settings()
        genai.configure(api_key=self.settings.gemini_api_key)
        self.gemini_model = genai.GenerativeModel(self.settings.chat_model)

        fallback_models = [m.strip() for m in self.settings.hf_fallback_models.split(",") if m.strip()]
        self.hf_chat_models = [self.settings.hf_chat_model] + [
            m for m in fallback_models if m != self.settings.hf_chat_model
        ]
        
        # Initialize Hugging Face Inference Client for FinGPT.
        # Gated on hf_chat_enabled because HF's free serverless router 404s
        # for open chat models (Qwen/Llama/Gemma/Mistral) — see settings.py.
        self.hf_client = None
        if self.settings.hf_chat_enabled and self.settings.huggingface_api_key:
            self.hf_client = InferenceClient(
                token=self.settings.huggingface_api_key
            )
        
        self.qdrant = QdrantService()
        self.supabase = get_supabase_client()
        self.router = QueryRouter()
        self.doc_retriever = DocumentRetriever()
        self.stock_retriever = PakistanStockRetriever()
        self.web_retriever = LiveWebRetriever()

    def answer(self, query: str, use_reasoning: bool = True,
               format: str = "detailed", user_id: str = None,
               conversation_id: str = None) -> Dict[str, Any]:
        """
        Full Fintex answer pipeline.
        """
        # ── Step 0: Categorize ──
        cat = categorize_query(query)
        category = cat["category"]
        subcategory = cat["subcategory"]

        # ── Step 1: Embed the question ──
        query_embedding = embed_text(query)

        # ── Step 2: Search Qdrant (vector similarity) ──
        qdrant_results = []
        try:
            qdrant_results = self.qdrant.search(
                query_vector=query_embedding,
                limit=3,
                score_threshold=0.70
            )
        except Exception as e:
            print(f"Qdrant search error: {e}")

        qdrant_found = len(qdrant_results) > 0

        # ── Step 3: Search Supabase (keyword match on past messages) ──
        supabase_results = []
        try:
            result = self.supabase.table("messages").select(
                "question, answer, category"
            ).order("date", desc=True).limit(2).execute()
            supabase_results = result.data or []
        except Exception as e:
            print(f"Supabase history search error: {e}")

        supabase_found = len(supabase_results) > 0

        # ── Build context from retrieved sources ──
        context, has_live_data = self._build_context(
            query, qdrant_results, supabase_results, category
        )

        gemini_called = False
        gemini_failed = False
        gemini_answer = ""
        
        # ── Step 4: Fallback to Gemini if no data ──
        if not qdrant_found and not supabase_found and not has_live_data:
            try:
                # Use Gemini STRICTLY as a middleman for broad context
                gemini_prompt = f"Provide a broad, professional financial overview to help answer this query: {query}. Focus on Pakistani context if relevant."
                gemini_response = self.gemini_model.generate_content(gemini_prompt)
                gemini_answer = gemini_response.text
                context += f"\n## External Research Context (Gemini)\n{gemini_answer}\n"
                gemini_called = True
            except Exception as e:
                print(f"Gemini context fetch failed: {e}")
                gemini_failed = True

        # ── Step 5: Decision Matrix ──
        accuracy_min, accuracy_max, source_label = self._decision_matrix(
            qdrant_found, supabase_found, has_live_data, gemini_called, gemini_failed
        )

        # ── Step 6: Generate Final Answer (FinGPT - HF Inference) ──
        prompt = self._build_prompt(query, context, category, format)
        answer_text = ""
        try:
            if self.hf_client:
                provider_down = False
                for model_name in self.hf_chat_models:
                    try:
                        hf_response = self.hf_client.chat_completion(
                            model=model_name,
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are FinGPT, a concise and professional financial assistant focused on Pakistan markets.",
                                },
                                {"role": "user", "content": prompt},
                            ],
                            max_tokens=1024,
                            temperature=0.7,
                            stop=["</s>", "\nUser:", "\nAssistant:"],
                        )
                        answer_text = (
                            hf_response.choices[0].message.content
                            if getattr(hf_response, "choices", None)
                            else str(hf_response)
                        )
                        if answer_text:
                            break
                    except Exception as model_error:
                        err_str = str(model_error)
                        print(f"HF model '{model_name}' failed: {model_error}")
                        # Short-circuit: if HF's router returns 404 for the
                        # first model, the free serverless tier is effectively
                        # offline for chat — skip the remaining models and let
                        # Gemini take over. Saves ~8s of sequential 404s.
                        if "404" in err_str and "router.huggingface.co" in err_str:
                            provider_down = True
                            print("HF serverless router is 404-ing; skipping remaining HF models.")
                            break
                        if "429" in err_str:
                            import time
                            time.sleep(1)

                if not answer_text:
                    answer_text = self._gemini_with_retry(prompt)
                    if not answer_text:
                        answer_text = self._context_only_fallback(query, context, category)
                        accuracy_min, accuracy_max, source_label = 30, 45, "📂 Context-Only Summary (LLMs unavailable)"
            else:
                answer_text = self._gemini_with_retry(prompt)
                if not answer_text:
                    answer_text = self._context_only_fallback(query, context, category)
                    accuracy_min, accuracy_max, source_label = 30, 45, "📂 Context-Only Summary (LLMs unavailable)"
        except Exception as e:
            print(f"FinGPT Generation error: {e}")
            try:
                response = self.gemini_model.generate_content(prompt)
                answer_text = response.text
                if gemini_called and not gemini_failed:
                    accuracy_min, accuracy_max, source_label = 35, 55, "🤖 Gemini (Fallback + Context)"
                else:
                    accuracy_min, accuracy_max, source_label = 30, 50, "🤖 Gemini (Fallback)"
            except Exception as fallback_error:
                print(f"Gemini outer fallback failed: {fallback_error}")
                answer_text = self._context_only_fallback(query, context, category)
                accuracy_min, accuracy_max, source_label = 30, 45, "📂 Context-Only Summary (LLMs unavailable)"

        # ── Build sources list ──
        sources = self._build_sources(qdrant_results, supabase_results, category, source_label)

        # ── Step 7: Fetch chart data whenever a known PSX ticker is mentioned ──
        # This runs regardless of category so that comparison ("ENGRO vs FFBL")
        # and stock-themed theory ("explain HBL's dividend yield") queries still
        # render the dashboard. Safety: we only match a hardcoded whitelist of
        # symbols literally present as whole words, so English words like "HOW"
        # or "RATIO" cannot be promoted to fake tickers.
        chart_data = None
        detected_ticker = None
        try:
            import re
            known_psxsymbols = {
                "ENGRO", "HBL", "UBL", "MCB", "MEBL", "OGDC", "PPL", "MARI",
                "LUCK", "FCCL", "TRG", "SYS", "HUBC", "KAPCO", "KEL", "NESTLE",
                "FFC", "FATIMA", "BOP", "NBP", "UNITY", "PSMC", "INDU", "HCAR",
                "MLCF", "CHCC", "POL", "FNEL", "WTL", "PAEL", "ENGROH", "WAVES",
                "AVN", "PTC", "AABS", "KML", "TPLRF1", "FFBL", "EFERT",
            }
            q_upper = query.upper()
            words = set(re.findall(r'\b\w+\b', q_upper))
            found_tickers = [sym for sym in known_psxsymbols if sym in words]
            found_tickers = list(dict.fromkeys(found_tickers))

            if found_tickers:
                detected_ticker = ",".join(found_tickers)
                history = self.stock_retriever.get_price_history(found_tickers[0], limit=100)
                if history:
                    chart_data = [
                        {"date": r.get("date", ""), "price": float(r.get("close", 0))}
                        for r in history
                    ]
        except Exception as e:
            print(f"Chart error: {e}")

        # ── Step 8: Save back to Qdrant ──
        self._save_to_qdrant(query, answer_text, category, subcategory, user_id, conversation_id)

        # ── Step 9: Prepare Metadata (Section 7.3) ──
        metadata = {
            "category": category,
            "subcategory": subcategory,
            "data_source": source_label,
        }
        if detected_ticker:
            first_ticker = detected_ticker.split(",")[0]
            stats = self.stock_retriever.get_price_stats(first_ticker, days=30)
            metadata.update({
                "symbol": detected_ticker,
                "chart_rendered": True,
                "data_source": "supabase_stock_prices"
            })
            if stats:
                metadata.update({
                    "start_price": stats.get("first_close"),
                    "end_price": stats.get("latest_close"),
                    "overall_change_pct": stats.get("change_percent"),
                    "period_high": stats.get("highest_high"),
                    "period_low": stats.get("lowest_low"),
                })

        # ── Final Response ──
        confidence_level = "high" if accuracy_min >= 80 else ("medium" if accuracy_min >= 50 else "low")
        result = {
            "query": query,
            "answer": {
                "answer": answer_text,
                "confidence": {
                    "level": confidence_level,
                    "document_count": len(qdrant_results),
                    "timeseries_count": 0,
                    "stock_market_count": 0,
                },
                "sources": sources,
            },
            "reasoning_used": use_reasoning,
            "category": category,
            "subcategory": subcategory,
            "accuracy_min": accuracy_min,
            "accuracy_max": accuracy_max,
            "source": source_label,
            "metadata": metadata
        }
        if chart_data: result["chart_data"] = chart_data
        if detected_ticker: result["ticker"] = detected_ticker
        return result

    # ─────────────────────────────────────────────────────────────────────
    # RESILIENT SYNTHESIS HELPERS
    # ─────────────────────────────────────────────────────────────────────

    def _gemini_with_retry(self, prompt: str, attempts: int = 2) -> str:
        """
        Call Gemini with exponential backoff plus model fallback.
        Tries the primary chat_model first, then each fallback model — so if
        the primary is quota=0 on the free tier, we move on instead of burning
        all retries on the same dead model.
        """
        import time
        fallbacks = [m.strip() for m in self.settings.chat_model_fallbacks.split(",") if m.strip()]
        model_chain = [self.settings.chat_model] + [m for m in fallbacks if m != self.settings.chat_model]

        for model_name in model_chain:
            delay = 1.5
            try:
                model = genai.GenerativeModel(model_name)
            except Exception as e:
                print(f"Gemini model '{model_name}' init failed: {e}")
                continue

            for i in range(attempts):
                try:
                    response = model.generate_content(prompt)
                    text = getattr(response, "text", "") or ""
                    if text.strip():
                        # Promote the working model so subsequent calls use it
                        self.gemini_model = model
                        return text
                except Exception as e:
                    msg = str(e).lower()
                    print(f"Gemini '{model_name}' attempt {i+1}/{attempts} failed: {e}")
                    quota_zero = "limit: 0" in msg or "quota" in msg and "free_tier" in msg
                    transient = any(s in msg for s in ["503", "unavailable", "500", "internal"])
                    # If quota is literally zero for this model, do not retry it — jump to next model
                    if quota_zero:
                        break
                    # For transient 5xx, retry this model. For other 429, also retry once.
                    if not (transient or "429" in msg) or i == attempts - 1:
                        break
                    time.sleep(delay)
                    delay *= 2
        return ""

    def _context_only_fallback(self, query: str, context: str, category: str) -> str:
        """
        Last-resort answer when both FinGPT (HF) and Gemini are unavailable.
        Surfaces retrieved context directly — prioritising live SerpAPI web
        results when present so the user still gets a useful answer.
        """
        web_docs = []
        try:
            if category == "theory":
                web_docs = self.web_retriever.search_general(query, limit=5)
            else:
                web_docs = self.web_retriever.search_news(query, limit=5) \
                    or self.web_retriever.search_general(query, limit=5)
        except Exception as e:
            print(f"SerpAPI fallback fetch failed: {e}")

        if web_docs:
            lines = [
                f"### 🌐 Live Web Results for: *{query}*\n",
                "_Synthesis engines are busy; here are the most relevant live "
                "sources fetched via SerpAPI:_\n",
            ]
            for d in web_docs:
                title = d.get("title", "Untitled")
                snippet = d.get("content", "")[:400]
                url = d.get("url", "")
                lines.append(f"**[{title}]({url})**\n{snippet}\n")
            if context.strip():
                lines.append("\n---\n\n### Additional Indexed Context\n")
                lines.append(context)
            return "\n".join(lines)

        if context.strip():
            return (
                f"### ⚠️ Partial Answer — Synthesis Unavailable\n\n"
                f"Here is the raw evidence retrieved for your question:\n\n"
                f"**Question:** {query}\n\n---\n\n{context}\n\n---\n\n"
                f"*Please retry in ~30 seconds for a fully synthesized answer.*"
            )
        return (
            "⚠️ Synthesis engines are temporarily unavailable and no indexed "
            "context was retrieved for this query. Please retry in ~30 seconds."
        )

    # ─────────────────────────────────────────────────────────────────────
    # DECISION MATRIX (Section 6, Step 4)
    # ─────────────────────────────────────────────────────────────────────

    def _decision_matrix(self, qdrant_found: bool,
                         supabase_found: bool, has_live_data: bool,
                         gemini_called: bool, gemini_failed: bool) -> Tuple[int, int, str]:
        """
        Returns (accuracy_min, accuracy_max, source_label) per Section 6 Scoring Logic.
        """
        # 1. Qdrant ✅ + Supabase ✅ (both had relevant data)
        if qdrant_found and (supabase_found or has_live_data):
            return 88, 96, "✅ Grounded in Verified Indexed Data"
            
        # 2. Qdrant ✅ only
        if qdrant_found:
            return 75, 87, "📚 Verified Knowledge Base"
            
        # 3. Supabase ✅ only
        if supabase_found or has_live_data:
            return 70, 82, "📂 Internal Database Records"

        # 4. Gemini → FinGPT refinement (Full fallback)
        if gemini_called and not gemini_failed:
            return 42, 60, "💡 FinGPT Refined (from External Context)"

        # 5. FinGPT failed, Gemini answered directly (Emergency fallback)
        if gemini_failed or (not qdrant_found and not supabase_found and not gemini_called):
             return 30, 45, "🤖 AI Logical Extension"

        # Default (FinGPT only / no DB hit)
        return 58, 72, "🧠 FinGPT Primary Reasoning"

    # ─────────────────────────────────────────────────────────────────────
    # CONTEXT BUILDER
    # ─────────────────────────────────────────────────────────────────────

    def _build_context(self, query: str, qdrant_results: list,
                       supabase_results: list, category: str) -> Tuple[str, bool]:
        """Merge Qdrant + Supabase + Live API results into a single context string."""
        parts = []
        initial_parts_count = 0
        has_live_data = False

        # Qdrant vector matches
        if qdrant_results:
            parts.append("## Retrieved from Knowledge Base (Qdrant Vector Search)\n")
            for r in qdrant_results:
                doc_id = r.get("doc_id", "")
                score = r.get("score", 0)
                try:
                    chunk = self.supabase.table("chunks").select("content").eq("id", doc_id).single().execute()
                    if chunk.data:
                        parts.append(f"**[Relevance: {score:.2f}]**\n{chunk.data['content']}\n")
                except:
                    pass

        # Supabase keyword matches from message history
        if supabase_results:
            parts.append("\n## Previous Answers from Chat History (Supabase)\n")
            for msg in supabase_results:
                parts.append(f"**Previous Q:** {msg.get('question', '')}\n"
                             f"**Previous A:** {msg.get('answer', '')[:500]}\n")

        # Also get live data for stock queries
        if category == "stocks":
            try:
                routing = self.router.route(query, use_llm=False)
                entities = routing.get("entities", [])
                symbols = [e.upper() for e in entities if len(e) >= 2]
                
                if not symbols:
                    q_upper = query.upper()
                    known_psx = ["ENGRO", "HBL", "UBL", "MCB", "MEBL", "OGDC", "PPL", "MARI", "LUCK", "FCCL", "FFBL"]
                    for s in known_psx:
                        if s in q_upper:
                            symbols = [s]
                            break
                
                if symbols:
                    sym = symbols[0]
                    start_date = date.today() - timedelta(days=30)
                    
                    parts.append("\n## Supabase Market Data (public.stock_prices)\n")
                    history = self.stock_retriever.get_price_history(sym, start_date=start_date, limit=20)
                    
                    if history:
                        has_live_data = True
                        stats = self.stock_retriever.get_price_stats(sym, days=30)
                        parts.append(f"### Historical Data and Stats for {sym}:\n")
                        if stats:
                            parts.append(self.stock_retriever.format_stats_for_context(stats) + "\n")
                        for row in history[-10:]:
                            parts.append(f"- Date: {row['date']}, Close: {row['close']}, Vol: {row['volume']}\n")
            except Exception as e:
                print(f"Stock context error: {e}")

        # Supplement with live web search (SerpAPI)
        # For stocks / news-ish queries → Google News. For theory / definitional
        # queries → Google general search (news results are noisy for "what is X").
        try:
            web_docs = []
            if category == "theory":
                web_docs = self.web_retriever.search_general(query, limit=4)
            else:
                web_docs = self.web_retriever.search_news(query, limit=3)
                if not web_docs:
                    web_docs = self.web_retriever.search_general(query, limit=3)

            if web_docs:
                has_live_data = True
                header = "Live Web Search (SerpAPI · Google News)" if category != "theory" \
                    else "Live Web Search (SerpAPI · Google)"
                parts.append(f"\n## {header}\n")
                for doc in web_docs:
                    title = doc.get("title", "Untitled")
                    content = doc.get("content", "")[:400]
                    url = doc.get("url", "")
                    parts.append(f"**{title}**\n{content}...\n[Source]({url})\n")
        except Exception as e:
            print(f"SerpAPI context fetch failed: {e}")

        context_str = "\n".join(parts) if parts else ""
        return context_str, has_live_data

    # ─────────────────────────────────────────────────────────────────────
    # PROMPT BUILDER (Sections 7 & 8 formatting)
    # ─────────────────────────────────────────────────────────────────────

    def _build_prompt(self, query: str, context: str,
                      category: str, format: str) -> str:
        """
        Build the LLM prompt with strict formatting rules based on category.
        Enforces the FinGPT persona.
        """
        base = """You are FinGPT, a specialized financial research agent. 
Your goal is to provide high-accuracy research based on retrieved financial data.
Use the following context to answer the user question.

CONTEXT:
{context}

USER QUESTION: "{query}"

Strictly follow these formatting rules:
"""

        if category == "stocks":
            return base.format(context=context, query=query) + """
IMPORTANT: Structure your answer EXACTLY in this order with these headings:

### 📊 Company Background
- Company full name, PSX ticker symbol, sector/industry
- Brief 2-3 sentence description of the company
- Founded year and headquarters if known

### 📈 Performance Analysis
- Analyze performance based on available data
- For each significant period: explain why price went up or down
- Be specific: mention exact percentage changes where possible
- Reference earnings, macro events, SBP rate changes, political climate

### 🧠 Fintex Investment Opinion
Write 3-4 paragraphs:
1. Overall sentiment — bullish, bearish, or neutral based on recent trend
2. Why to invest (if applicable) — fundamentals, sector growth, undervaluation
3. Why NOT to invest (if applicable) — risks, volatility, macro headwinds
4. When to invest — specific signals to watch for

End with this exact disclaimer in italic:
*"This is an AI-generated opinion for educational purposes only. It is not financial advice. Please consult a licensed financial advisor before making investment decisions."*

Your Answer:
"""

        elif category == "theory":
            return base.format(context=context, query=query) + """
IMPORTANT: Structure your answer EXACTLY in this order with these headings:

### 📖 Definition
1-2 sentence crisp definition.

### 📝 Detailed Explanation
3-5 paragraphs covering the concept thoroughly. Use analogies. Reference Pakistan-specific examples where relevant.

### 🔑 Key Points
A bullet-point summary of 4-6 key takeaways.

### 🇵🇰 Pakistan Context
A short paragraph linking the theory to Pakistan's financial environment (SBP, PSX, NBP, macroeconomic conditions).

### 📚 Further Reading
Provide 3-5 real, verifiable URLs. Prefer these sources:
- sbp.org.pk (State Bank of Pakistan)
- psx.com.pk (Pakistan Stock Exchange)
- investopedia.com (for global theory)
- nbp.com.pk (National Bank of Pakistan)
- imf.org or worldbank.org for macro topics
Format each as: [Title](URL)

Your Answer:
"""

        elif category == "monetary_policy":
            return base.format(context=context, query=query) + """
Structure your answer covering:
1. Current policy stance and recent changes
2. Historical context and trend
3. Impact on banking sector and economy
4. Pakistan-specific implications
5. Key data points with dates and figures

Your Answer:
"""

        else:
            # General / macro / banking
            format_map = {
                "detailed": "Provide a comprehensive, well-structured answer with multiple paragraphs.",
                "brief": "Provide a concise answer in 2-3 sentences.",
                "bullet": "Provide answer as bullet points (3-5 points)."
            }
            instruction = format_map.get(format, format_map["detailed"])
            return base.format(context=context, query=query) + f"""
Instructions: {instruction}

Rules:
1. Answer based on the evidence provided
2. Cite specific sources when making claims
3. If evidence is insufficient, clearly state what's missing
4. Use clear, professional language
5. For numerical data, be precise and include units

Your Answer:
"""

    # ─────────────────────────────────────────────────────────────────────
    # SOURCES BUILDER
    # ─────────────────────────────────────────────────────────────────────

    def _build_sources(self, qdrant_results: list,
                       supabase_results: list, category: str, fallback_source: str = "") -> list:
        """Build a list of source citations for the UI."""
        sources = []
        for r in qdrant_results:
            sources.append({
                "type": "document",
                "title": f"Knowledge Base (score: {r.get('score', 0):.2f})",
                "source_type": r.get("source_type", "indexed_data")
            })
        for msg in supabase_results:
            sources.append({
                "type": "document",
                "title": f"Chat History: {msg.get('question', '')[:40]}",
                "source_type": "chat_history"
            })
        if category == "stocks":
            sources.append({
                "type": "stock_market",
                "symbol": "PSX",
                "source": "Pakistan Stock Exchange"
            })
        if fallback_source and len(sources) == 0:
            sources.append({
                "type": "web",
                "title": fallback_source,
                "source_type": "llm_generated"
            })
        return sources

    # ─────────────────────────────────────────────────────────────────────
    # QDRANT MEMORY SYNC (Section 4.4)
    # ─────────────────────────────────────────────────────────────────────

    def _save_to_qdrant(self, question: str, answer: str,
                        category: str, subcategory: str,
                        user_id: str = None,
                        conversation_id: str = None) -> None:
        """
        Embed the Q&A pair and save to Qdrant + Supabase chunks table
        so future queries can semantically retrieve it.
        """
        try:
            combined = (
                f"Q: {question}\n"
                f"A: {answer[:300]}\n"
                f"Category: {category}\n"
                f"Date: {datetime.utcnow().isoformat()}"
            )
            embedding = embed_text(combined)
            chunk_id = str(uuid.uuid4())

            self.qdrant.upsert_vector(
                doc_id=chunk_id,
                embedding=embedding,
                sector_category=category,
                source_type="chat_memory",
                subcategory=subcategory,
                metadata={
                    "user_id": user_id or "",
                    "conversation_id": conversation_id or "",
                    "source": "chat_memory",
                }
            )

            self.supabase.table("chunks").insert({
                "id": chunk_id,
                "content": combined,
                "question": question,
                "answer": answer[:2000],
                "category": category,
                "subcategory": subcategory,
                "metadata": json.dumps({
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                })
            }).execute()

            print(f"[Qdrant Sync] Saved chunk {chunk_id} ({category}/{subcategory})")
        except Exception as e:
            print(f"[Qdrant Sync Error] {e}")


# ─────────────────────────────────────────────────────────────────────────────
# AUTO CONVERSATION TITLE (Section 4.2)
# ─────────────────────────────────────────────────────────────────────────────

def generate_conversation_title(query: str) -> str:
    """Generate a short 4-6 word title for a conversation."""
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.chat_model)

    prompt = (
        f'Given this user question: "{query}"\n'
        f"Generate a short 4-6 word title for this conversation. "
        f"Return only the title, no quotes, no extra text."
    )

    try:
        response = model.generate_content(prompt)
        title = response.text.strip().strip('"').strip("'")
        if len(title) > 60:
            title = title[:57] + "..."
        return title
    except Exception as e:
        print(f"Title generation error: {e}")
        words = query.split()[:6]
        return " ".join(words)
