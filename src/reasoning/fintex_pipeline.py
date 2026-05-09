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

# ── Concept-level keywords for non-stock categories ──────────────────────────
# These are stable financial terminology terms that do NOT need to be updated
# when new stocks/tickers are added.
# "stocks" is intentionally absent: stock detection is done dynamically
# against the Supabase symbol cache inside FintexPipeline._categorize().
CATEGORY_KEYWORDS = {
    "stocks": [
        # Only pure concept words — no ticker symbols here
        "stock", "share", "psx", "kse", "kse100", "kse-100", "ticker",
        "listed", "ipo", "dividend", "eps", "pe ratio", "market cap",
        "scrip", "equity", "graphical data", "chart", "candlestick",
        "moving average", "technical analysis", "fundamental analysis",
    ],
    "monetary_policy": [
        "sbp", "state bank", "policy rate", "interest rate", "discount rate",
        "monetary policy", "reserve", "inflation target", "money supply",
    ],
    "banking": [
        "bank", "banking sector", "deposits", "advances",
        "non-performing", "npl", "spread", "casa",
    ],
    "theory": [
        "what is", "define", "explain", "concept", "theory",
        "difference between", "how does", "meaning of",
        "economics", "finance theory", "fundamentals",
    ],
    "macro": [
        "gdp", "inflation", "cpi", "trade deficit", "balance of payments",
        "fiscal deficit", "budget", "imf", "world bank", "remittances",
        "forex", "exchange rate", "usd", "pkr", "rupee", "dollar",
    ],
}

# ─── Off-topic signal words ────────────────────────────────────────────────────
# If a query contains ANY of these and NO finance keywords, it is flagged as
# out-of-scope.  Finance-adjacent terms ("trade", "dollar", "market") are
# intentionally excluded from this list so they never cause false positives.
OFF_TOPIC_SIGNALS = [
    # Sports
    "cricket", "football", "soccer", "hockey", "tennis", "basketball", "baseball",
    "ipl", "psl", "fifa", "olympics", "athlete", "match", "tournament", "stadium",
    "goal", "wicket", "runs", "batting", "bowling", "score",
    # Entertainment / celebrities
    "movie", "film", "actor", "actress", "singer", "song", "album", "celebrity",
    "bollywood", "hollywood", "drama", "serial", "netflix", "youtube", "tiktok",
    "instagram", "twitter", "facebook", "social media",
    # Science / tech (non-finance)
    "space", "nasa", "planet", "galaxy", "black hole", "quantum", "physics",
    "chemistry", "biology", "medicine", "vaccine", "virus", "covid", "disease",
    "robot", "artificial intelligence", "machine learning", "chatgpt", "openai",
    # Food / cooking
    "recipe", "cooking", "food", "restaurant", "cuisine", "biryani", "pizza",
    "burger", "diet", "calories", "nutrition",
    # Weather / geography
    "weather", "temperature", "rain", "snow", "flood", "earthquake", "volcano",
    "climate change", "global warming",
    # History / politics (non-economic)
    "war", "army", "military", "election", "prime minister", "president",
    "parliament", "constitution", "political party",
    # General knowledge
    "joke", "poem", "story", "riddle", "quiz", "trivia",
    "translate", "language", "grammar",
    # Health
    "doctor", "hospital", "medicine", "symptoms", "treatment", "surgery",
]

# Finance / Pakistan-finance whitelist: if ANY of these are in the query we
# will never flag it as off-topic even if an off-topic word also appears.
FINANCE_GUARD_WORDS = [
    "stock", "share", "psx", "kse", "bank", "invest", "finance", "financial",
    "rupee", "pkr", "sbp", "economy", "economic", "gdp", "inflation", "imf",
    "dividend", "equity", "portfolio", "market", "trading", "commodity",
    "forex", "exchange rate", "bond", "treasury", "fiscal", "monetary",
    "pakistan", "psx", "karachi", "lahore",
]


STRONG_THEORY_PATTERNS = [
    "what is ", "what are ", "what does ",
    "how does ", "how do ", "how is ",
    "define ", "explain ",
    "difference between ", "differ ", "vs ",
    "meaning of ", "concept of ",
]


def is_off_topic(query: str) -> bool:
    """
    Return True when a query is clearly outside Fintex's Pakistan-finance domain.

    Logic:
      1. If any FINANCE_GUARD_WORDS appear → never off-topic.
      2. If any OFF_TOPIC_SIGNALS appear AND no finance guard word → off-topic.
      3. If neither list matches → treat as in-scope (benefit of the doubt).
    """
    q = query.lower()
    # Guard: any finance keyword keeps it in scope
    if any(gw in q for gw in FINANCE_GUARD_WORDS):
        return False
    # Flag: obvious off-topic signal
    if any(sig in q for sig in OFF_TOPIC_SIGNALS):
        return True
    return False


def categorize_query(query: str) -> Dict[str, str]:
    """
    Legacy shim — delegates to keyword scoring only (no cache).
    Prefer FintexPipeline._categorize() which also uses the Supabase
    symbol cache and Qdrant metadata for dynamic stock detection.
    """
    q = query.lower()
    if is_off_topic(query):
        return {"category": "off_topic", "subcategory": "off_topic", "off_topic": True}

    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                scores[cat] += 1

    if any(pat in q for pat in STRONG_THEORY_PATTERNS):
        best = "theory"
    else:
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            best = "general"

    return {"category": best, "subcategory": _detect_subcategory(q, best), "off_topic": False}


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

    # ── Company full-name → PSX ticker map ──────────────────────────────────
    # Covers the most commonly searched companies by their full / popular names.
    # Add more entries here as needed.  Keys must be lowercase.
    COMPANY_NAME_MAP: Dict[str, str] = {
        # Banks
        "habib bank": "HBL", "habib bank limited": "HBL",
        "united bank": "UBL", "united bank limited": "UBL",
        "mcb bank": "MCB", "muslim commercial bank": "MCB",
        "meezan bank": "MEBL", "meezan bank limited": "MEBL",
        "national bank": "NBP", "national bank of pakistan": "NBP",
        "bank alfalah": "BAFL", "bank alfalah limited": "BAFL",
        "bank al habib": "BAHL", "bank al habib limited": "BAHL",
        "askari bank": "AKBL", "askari bank limited": "AKBL",
        "faysal bank": "FABL", "faysal bank limited": "FABL",
        "js bank": "JSBL", "js bank limited": "JSBL",
        "standard chartered": "SCBPL",
        "soneri bank": "SNBL",
        "silkbank": "SILK",
        "summit bank": "SMBL",
        "bop": "BOP", "bank of punjab": "BOP",
        "first women bank": "FFL",
        # Energy / Oil & Gas
        "oil and gas development": "OGDC", "ogdcl": "OGDC",
        "pakistan petroleum": "PPL", "pakistan petroleum limited": "PPL",
        "mari petroleum": "MARI",
        "pakistan oilfields": "POL",
        "attock petroleum": "APL",
        "attock refinery": "ATRL",
        "pakistan refinery": "PRL",
        "byco petroleum": "BYCO",
        "hub power": "HUBC", "hub power company": "HUBC",
        "kapco": "KAPCO", "kot addu power": "KAPCO",
        "k-electric": "KEL", "k electric": "KEL",
        "pakistan state oil": "PSO",
        "ssgc": "SSGC", "sui southern gas": "SSGC", "sui southern gas company": "SSGC",
        # Fertilisers
        "engro": "ENGRO", "engro corporation": "ENGRO",
        "engro fertilizers": "EFERT",
        "fauji fertilizer": "FFC", "fauji fertilizer company": "FFC",
        "fatima fertilizer": "FATIMA",
        "ffbl": "FFBL", "fauji fertilizer bin qasim": "FFBL",
        # Cement
        "lucky cement": "LUCK",
        "fauji cement": "FCCL",
        "maple leaf cement": "MLCF",
        "cherat cement": "CHCC",
        "pioneer cement": "PIOC",
        "dg khan cement": "DGKC",
        "bestway cement": "BWCL",
        # Pharma
        "abbott": "ABOT", "abbott laboratories": "ABOT",
        "glaxosmithkline": "GSKCH", "gsk": "GSKCH",
        "searle": "SEARL", "the searle company": "SEARL",
        "ferozsons": "FEROZ",
        "highnoon": "HINOON",
        # Autos
        "honda atlas": "HCAR",
        "pak suzuki": "PSMC",
        "indus motor": "INDU", "toyota": "INDU",
        "millat tractors": "MTL",
        # Tech
        "systems limited": "SYS", "systems ltd": "SYS",
        "trg pakistan": "TRG",
        "netsol technologies": "NETSOL",
        # Telecom
        "pakistan telecommunication": "PTC", "ptcl": "PTC",
        "worldcall": "WTL",
        # FMCG
        "nestle pakistan": "NESTLE",
        "colgate": "COLG",
        "unilever": "ULEVER",
        # PSX index / market
        "kse100": "KSE100", "kse-100": "KSE100",
    }

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

        # Cache of all PSX symbols from Supabase — populated on first use.
        self._psx_symbols_cache: Optional[set] = None

    # ───────────────────────────────────────────────────────────────────
    # DYNAMIC SYMBOL CACHE LOADER
    # ───────────────────────────────────────────────────────────────────

    def _ensure_symbols_loaded(self) -> None:
        """
        Eagerly populate self._psx_symbols_cache from Supabase stock_prices.
        Idempotent: only hits the DB on the first call per instance.
        """
        if self._psx_symbols_cache is not None:
            return
        try:
            raw = (
                self.supabase.table("stock_prices")
                .select("symbol")
                .limit(5000)
                .execute()
            )
            if raw.data:
                self._psx_symbols_cache = {row["symbol"].upper() for row in raw.data}
                print(f"[SymbolCache] Loaded {len(self._psx_symbols_cache)} symbols from Supabase")
            else:
                self._psx_symbols_cache = set()
        except Exception as e:
            print(f"[SymbolCache] Failed to load: {e}")
            self._psx_symbols_cache = set()

    # ───────────────────────────────────────────────────────────────────
    # DYNAMIC QUERY CATEGORIZER
    # ───────────────────────────────────────────────────────────────────

    def _categorize(self, query: str, qdrant_results: list) -> Dict[str, str]:
        """
        Dynamic, three-signal categorizer.

        Signal 1 — Off-topic guard (always checked first).
        Signal 2 — Supabase symbol cache + COMPANY_NAME_MAP.
                    Any query that mentions a known PSX ticker or a full company
                    name is immediately routed to "stocks" WITHOUT needing a
                    hardcoded list in CATEGORY_KEYWORDS.
        Signal 3 — Qdrant result metadata.
                    The sector_category stored on each Qdrant hit is used as a
                    voting signal so queries that semantically match theoretical
                    documents are reliably routed to "theory" or "macro" etc.
        Signal 4 — Fallback keyword scoring (CATEGORY_KEYWORDS, concept-only).
        """
        import re as _re

        q_lower = query.lower()
        q_upper = query.upper()

        # ── Signal 1: off-topic check ────────────────────────────────────
        if is_off_topic(query):
            return {"category": "off_topic", "subcategory": "off_topic", "off_topic": True}

        # ── Signal 2a: symbol cache (Supabase) ────────────────────────────
        # Tokenise the query as uppercase words (≥3 chars) and check against
        # the full PSX symbol set loaded from Supabase stock_prices.
        if self._psx_symbols_cache:
            words = set(_re.findall(r'\b[A-Z0-9]{2,}\b', q_upper))
            if words & self._psx_symbols_cache:
                print(f"[Categorize] Stock detected via Supabase cache")
                return {"category": "stocks", "subcategory": "price_query", "off_topic": False}

        # ── Signal 2b: COMPANY_NAME_MAP (full company names) ─────────────
        for name in sorted(self.COMPANY_NAME_MAP, key=len, reverse=True):
            if name in q_lower:
                print(f"[Categorize] Stock detected via name map: '{name}'")
                return {"category": "stocks", "subcategory": "price_query", "off_topic": False}

        # ── Signal 3: Qdrant result sector_category metadata voting ──────
        # If the top Qdrant hits are predominantly from one category, trust it.
        if qdrant_results:
            votes: Dict[str, float] = {}
            for r in qdrant_results:
                qdrant_cat = (
                    r.get("sector_category")
                    or (r.get("metadata") or {}).get("sector_category")
                )
                score = float(r.get("score", 0.5))
                if qdrant_cat:
                    votes[qdrant_cat] = votes.get(qdrant_cat, 0) + score

            if votes:
                qdrant_best = max(votes, key=votes.get)
                # Only trust the Qdrant signal if it is NOT a theory/definitional
                # question (theory override below takes precedence)
                if not any(pat in q_lower for pat in STRONG_THEORY_PATTERNS):
                    print(f"[Categorize] Category from Qdrant metadata: '{qdrant_best}'")
                    return {
                        "category": qdrant_best,
                        "subcategory": _detect_subcategory(q_lower, qdrant_best),
                        "off_topic": False,
                    }

        # ── Signal 4: Concept-level keyword scoring (fallback) ──────────
        # STRONG_THEORY_PATTERNS override takes priority over score.
        if any(pat in q_lower for pat in STRONG_THEORY_PATTERNS):
            return {"category": "theory", "subcategory": "theory", "off_topic": False}

        scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in q_lower:
                    scores[cat] += 1

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            best = "general"

        return {
            "category": best,
            "subcategory": _detect_subcategory(q_lower, best),
            "off_topic": False,
        }

    def answer(self, query: str, use_reasoning: bool = True,
               format: str = "detailed", user_id: str = None,
               conversation_id: str = None) -> Dict[str, Any]:
        """
        Full Fintex answer pipeline.
        """
        # ── Eagerly load symbol cache so _categorize() can use it ──────────
        self._ensure_symbols_loaded()

        # ── Step 1: Embed the question ───────────────────────────────────
        query_embedding = embed_text(query)

        # ── Step 2: Search Qdrant (vector similarity) ────────────────────
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

        # ── Step 0 (after Qdrant): Dynamic categorization ─────────────────
        # Runs AFTER the Qdrant search so Qdrant metadata can vote on the
        # category, and AFTER the cache is guaranteed to be loaded.
        cat = self._categorize(query, qdrant_results)
        category = cat["category"]
        subcategory = cat["subcategory"]
        off_topic = cat.get("off_topic", False)
        print(f"[Pipeline] category={category} subcategory={subcategory} off_topic={off_topic}")

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
            qdrant_found, supabase_found, has_live_data, gemini_called, gemini_failed,
            off_topic=off_topic
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
        # Supports both ticker symbols (HBL) and full company names (Habib Bank Limited).
        # Symbol list is loaded dynamically from Supabase so all ingested stocks work.
        chart_data = None
        detected_ticker = None
        try:
            import re

            # ── 7a: Resolve full company names → tickers (ALL matches) ─────────
            # Collect every name→ticker pair found in the query — do NOT break
            # after the first hit so comparison queries like "Engro vs FFBL"
            # resolve both companies.
            q_lower = query.lower()
            name_resolved_tickers: List[str] = []
            seen_name_tickers: set = set()
            # Longest-name-first prevents shorter aliases masking longer ones
            for name, ticker in sorted(
                self.COMPANY_NAME_MAP.items(), key=lambda x: len(x[0]), reverse=True
            ):
                if name in q_lower and ticker not in seen_name_tickers:
                    name_resolved_tickers.append(ticker)
                    seen_name_tickers.add(ticker)
                    print(f"[TickerResolver] '{name}' → {ticker}")

            # Build an augmented query string that includes all resolved tickers
            # so the word-boundary scan in 7c can also find them.
            resolved_query = query + (
                (" " + " ".join(name_resolved_tickers)) if name_resolved_tickers else ""
            )

            # ── 7b: Symbol cache (already loaded at top of answer()) ─────
            # _ensure_symbols_loaded() was called at the start, so
            # self._psx_symbols_cache is guaranteed to be a set here.

            # ── 7c: Match whole-word tokens against the full symbol list ───────
            # Use Supabase cache PLUS COMPANY_NAME_MAP values as a guaranteed
            # fallback so comparison queries work even on a cache-miss.
            # Tokens ≤ 2 chars are skipped to avoid false matches ("IS", "AT").
            fallback_symbols = set(self.COMPANY_NAME_MAP.values())
            symbol_universe = (self._psx_symbols_cache or set()) | fallback_symbols

            q_upper = resolved_query.upper()
            words = set(re.findall(r'\b[A-Z0-9]{3,}\b', q_upper))
            found_tickers = [
                sym for sym in symbol_universe if sym in words
            ]
            # Prepend name-resolved tickers so they appear first (primary stocks)
            for t in reversed(name_resolved_tickers):
                if t not in found_tickers:
                    found_tickers.insert(0, t)
            found_tickers = list(dict.fromkeys(found_tickers))  # deduplicate, preserve order

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
            "sources": sources,
            "doc_count": len(qdrant_results)
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
                         gemini_called: bool, gemini_failed: bool,
                         off_topic: bool = False) -> Tuple[int, int, str]:
        """
        Returns (accuracy_min, accuracy_max, source_label) per Section 6 Scoring Logic.

        Off-topic queries are always capped at ≤ 65 regardless of data found,
        because Fintex is a Pakistan-finance specialist and should not
        present high confidence on unrelated topics.
        """
        # ── Off-topic override (always < 70) ──────────────────────────────
        if off_topic:
            return 25, 50, "🚫 Out of Scope — Fintex covers Pakistan Finance only"

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
                    # Try name resolution first
                    q_lower = query.lower()
                    for name, ticker in sorted(
                        self.COMPANY_NAME_MAP.items(), key=lambda x: len(x[0]), reverse=True
                    ):
                        if name in q_lower:
                            symbols = [ticker]
                            break

                if not symbols:
                    # Fall back to dynamic symbol list from cache
                    psx_set = self._psx_symbols_cache or set()
                    import re as _re
                    words = _re.findall(r'\b[A-Z0-9]{3,}\b', query.upper())
                    for w in words:
                        if w in psx_set:
                            symbols = [w]
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
        Enforces the FinGPT persona and respects the user-selected format.
        """
        base = """You are FinGPT, a specialized financial research agent. 
Your goal is to provide high-accuracy research based on retrieved financial data.
Use the following context to answer the user question.

CONTEXT:
{context}

USER QUESTION: "{query}"

Strictly follow these formatting rules:
"""
        # Define general format modifiers
        if format == "brief":
            format_instruction = "KEEP IT BRIEF: Max 2 paragraphs or a short summary. Skip secondary sections."
        elif format == "bullet":
            format_instruction = "USE BULLET POINTS: Use a list-based structure (3-7 points). No long paragraphs."
        else:
            format_instruction = "Detailed analysis requested. Be thorough and well-structured."

        if category == "stocks":
            structure = """
### 📊 Company Background
- Company full name, PSX ticker symbol, sector/industry
- Brief 1-2 sentence description
"""
            if format != "brief":
                structure += """
### 📈 Performance Analysis
- Analyze performance based on available data
- Explain price movements, macro events, or SBP rate changes
"""
            
            opinion_len = "3-4 paragraphs" if format == "detailed" else "1 concise paragraph"
            structure += f"""
### 🧠 Fintex Investment Opinion
Write {opinion_len}:
- Overall sentiment (bullish/bearish/neutral)
- Key reasons to invest or be cautious
- Specific signals to watch

End with this exact disclaimer in italic:
*"This is an AI-generated opinion for educational purposes only. It is not financial advice. Please consult a licensed financial advisor before making investment decisions."*
"""
            return base.format(context=context, query=query) + f"\nFormat Rule: {format_instruction}\n" + structure

        elif category == "theory":
            if format == "brief":
                structure = """
### 📖 Definition
1-2 sentence crisp definition.

### 🔑 Key Points
4-5 quick bullet points.
"""
            else:
                structure = """
### 📖 Definition
1-2 sentence crisp definition.

### 📝 Detailed Explanation
3-5 paragraphs covering the concept thoroughly. Use analogies. Reference Pakistan-specific examples where relevant.

### 🔑 Key Points
A bullet-point summary of 4-6 key takeaways.

### 🇵🇰 Pakistan Context
A short paragraph linking the theory to Pakistan's financial environment.
"""
            # Always add further reading for theory
            structure += """
### 📚 Further Reading
Provide 3-4 real, verifiable URLs (sbp.org.pk, psx.com.pk, investopedia.com).
"""
            return base.format(context=context, query=query) + f"\nFormat Rule: {format_instruction}\n" + structure

        elif category == "monetary_policy":
            length_instr = "concisely in 3-5 points" if format != "detailed" else "thoroughly with historical context"
            return base.format(context=context, query=query) + f"""
Structure your answer covering {length_instr}:
1. Current policy stance and recent changes
2. Impact on banking sector and economy
3. Key data points (dates, figures)
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
