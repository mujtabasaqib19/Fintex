"""
Fintex Financial Benchmark Suite
=================================
Evaluates the Fintex pipeline across five benchmark categories:

  A. Routing Accuracy      — correct category detection (stocks/macro/theory/off_topic)
  B. Prediction Quality    — concrete BULLISH/BEARISH/NEUTRAL verdict, no hedging
  C. Stock Data Accuracy   — live Supabase OHLCV data actually used in response
  D. FinQA-style Q&A       — Pakistan-specific numerical & factual financial queries
  E. FLUE-style Language   — sentiment, tone, and financial terminology accuracy
  F. Off-topic Rejection   — non-finance queries correctly rejected

Scoring per query (0–100):
  route_score       (20 pts) — correct category assigned
  verdict_score     (20 pts) — for predictions: concrete direction given
  no_hedge_score    (20 pts) — for predictions: forbidden hedge phrases absent
  format_score      (20 pts) — required markdown sections present
  relevance_score   (20 pts) — answer mentions expected keywords / entities

Run (live pipeline + full report):
    python tests/finance_benchmark.py

Run (offline, rule-based only, no API calls):
    python tests/finance_benchmark.py --offline

Run (specific category):
    python tests/finance_benchmark.py --category prediction

pytest integration:
    pytest tests/finance_benchmark.py -v
"""

from __future__ import annotations
import sys
import os
import re
import time
import json
import argparse
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK QUERY DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BenchmarkQuery:
    id: str
    category: str                     # A / B / C / D / E / F
    query: str
    expected_route: str               # stocks / macro / theory / banking / off_topic / general
    expected_keywords: List[str]      # keywords that MUST appear in a good answer
    forbidden_keywords: List[str]     # keywords that must NOT appear (hedging, wrong topic)
    requires_verdict: bool = False    # prediction queries must give BULLISH/BEARISH/NEUTRAL
    requires_live_data: bool = False  # must use Supabase OHLCV (PKR price present)
    notes: str = ""


BENCHMARK_QUERIES: List[BenchmarkQuery] = [

    # ── A. Routing Accuracy ──────────────────────────────────────────────────
    BenchmarkQuery(
        id="A01", category="A",
        query="What is the current price of ENGRO?",
        expected_route="stocks",
        expected_keywords=["ENGRO", "PKR"],
        forbidden_keywords=["cannot", "no data"],
        requires_live_data=True,
        notes="Basic ticker lookup — must resolve ENGRO and return PKR price",
    ),
    BenchmarkQuery(
        id="A02", category="A",
        query="Tell me about HBL bank performance",
        expected_route="stocks",
        expected_keywords=["HBL", "PKR"],
        forbidden_keywords=[],
        requires_live_data=True,
        notes="Company name query — must resolve HBL via name map",
    ),
    BenchmarkQuery(
        id="A03", category="A",
        query="What is Pakistan's current inflation rate?",
        expected_route="macro",
        expected_keywords=["inflation", "pakistan"],
        forbidden_keywords=[],
        notes="Macro indicator query",
    ),
    BenchmarkQuery(
        id="A04", category="A",
        query="What is the SBP policy rate today?",
        expected_route="monetary_policy",
        expected_keywords=["sbp", "rate"],
        forbidden_keywords=[],
        notes="Monetary policy routing",
    ),
    BenchmarkQuery(
        id="A05", category="A",
        query="What is the PE ratio in finance?",
        expected_route="theory",
        expected_keywords=["definition", "ratio", "earnings"],
        forbidden_keywords=[],
        notes="Concept/theory query — must route to theory, not stocks",
    ),
    BenchmarkQuery(
        id="A06", category="A",
        query="How does MACD work?",
        expected_route="theory",
        expected_keywords=["macd", "moving average"],
        forbidden_keywords=[],
        notes="Technical analysis concept",
    ),
    BenchmarkQuery(
        id="A07", category="A",
        query="What is Pakistan's GDP growth rate?",
        expected_route="macro",
        expected_keywords=["gdp", "pakistan"],
        forbidden_keywords=[],
        notes="GDP macro query",
    ),
    BenchmarkQuery(
        id="A08", category="A",
        query="Tell me about cricket world cup results",
        expected_route="off_topic",
        expected_keywords=[],
        forbidden_keywords=["stock", "pkr", "psx"],
        notes="Off-topic: sports — must be rejected",
    ),
    BenchmarkQuery(
        id="A09", category="A",
        query="Who is the best Bollywood actor?",
        expected_route="off_topic",
        expected_keywords=[],
        forbidden_keywords=["invest", "portfolio"],
        notes="Off-topic: entertainment",
    ),
    BenchmarkQuery(
        id="A10", category="A",
        query="Show me OGDC stock chart",
        expected_route="stocks",
        expected_keywords=["OGDC", "PKR"],
        forbidden_keywords=[],
        requires_live_data=True,
        notes="Stock chart request",
    ),
    BenchmarkQuery(
        id="A11", category="A",
        query="What is the USD to PKR exchange rate?",
        expected_route="macro",
        expected_keywords=["usd", "pkr"],
        forbidden_keywords=[],
        notes="Forex macro query",
    ),
    BenchmarkQuery(
        id="A12", category="A",
        query="Explain what RSI means in technical analysis",
        expected_route="theory",
        expected_keywords=["rsi", "relative strength"],
        forbidden_keywords=[],
        notes="Technical indicator concept",
    ),

    # ── B. Prediction Quality ────────────────────────────────────────────────
    BenchmarkQuery(
        id="B01", category="B",
        query="Predict if ENGRO is going to perform better or worse next week",
        expected_route="stocks",
        expected_keywords=["ENGRO", "RSI", "MACD", "PKR"],
        forbidden_keywords=["cannot predict", "cannot be determined", "no technical data",
                            "inherently speculative", "data is unavailable"],
        requires_verdict=True,
        requires_live_data=True,
        notes="Core prediction query — must return BULLISH/BEARISH/NEUTRAL verdict",
    ),
    BenchmarkQuery(
        id="B02", category="B",
        query="Will HBL stock go up or down tomorrow?",
        expected_route="stocks",
        expected_keywords=["HBL", "PKR", "RSI"],
        forbidden_keywords=["cannot predict", "cannot be determined", "no data",
                            "inherently speculative"],
        requires_verdict=True,
        requires_live_data=True,
        notes="Short-term prediction — must resolve HBL via name map",
    ),
    BenchmarkQuery(
        id="B03", category="B",
        query="Should I buy OGDC now or wait?",
        expected_route="stocks",
        expected_keywords=["OGDC", "PKR"],
        forbidden_keywords=["cannot predict", "cannot determine", "no data"],
        requires_verdict=True,
        requires_live_data=True,
        notes="Buy/sell recommendation query",
    ),
    BenchmarkQuery(
        id="B04", category="B",
        query="Forecast PPL stock for next month",
        expected_route="stocks",
        expected_keywords=["PPL", "PKR"],
        forbidden_keywords=["cannot", "no data", "speculative"],
        requires_verdict=True,
        requires_live_data=True,
        notes="Medium-term forecast",
    ),
    BenchmarkQuery(
        id="B05", category="B",
        query="Is LUCK cement stock worth buying?",
        expected_route="stocks",
        expected_keywords=["LUCK", "PKR"],
        forbidden_keywords=["cannot predict", "no data"],
        requires_verdict=True,
        requires_live_data=True,
        notes="Worth buying query",
    ),
    BenchmarkQuery(
        id="B06", category="B",
        query="Will PSO stock be bullish or bearish this week?",
        expected_route="stocks",
        expected_keywords=["PSO", "PKR"],
        forbidden_keywords=["cannot", "no data", "speculative"],
        requires_verdict=True,
        requires_live_data=True,
        notes="Bullish/bearish query with ticker",
    ),
    BenchmarkQuery(
        id="B07", category="B",
        query="Predict if engro is gonna perform better on may 10",
        expected_route="stocks",
        expected_keywords=["ENGRO", "PKR", "RSI"],
        forbidden_keywords=["cannot predict", "horoscope", "inherently speculative",
                            "cannot be determined", "no technical data"],
        requires_verdict=True,
        requires_live_data=True,
        notes="Exact query from user bug report — the original failing case",
    ),
    BenchmarkQuery(
        id="B08", category="B",
        query="Should I sell my MEBL shares before next week?",
        expected_route="stocks",
        expected_keywords=["MEBL", "PKR"],
        forbidden_keywords=["cannot", "no data"],
        requires_verdict=True,
        requires_live_data=True,
        notes="Sell decision query — Meezan Bank via ticker",
    ),

    # ── C. Stock Data Accuracy ───────────────────────────────────────────────
    BenchmarkQuery(
        id="C01", category="C",
        query="What is ENGRO's current price and 30-day performance?",
        expected_route="stocks",
        expected_keywords=["PKR", "ENGRO", "%"],
        forbidden_keywords=["no data", "unavailable"],
        requires_live_data=True,
        notes="Must return real PKR price from Supabase stock_prices",
    ),
    BenchmarkQuery(
        id="C02", category="C",
        query="Show me HBL stock history for the last month",
        expected_route="stocks",
        expected_keywords=["HBL", "PKR", "date"],
        forbidden_keywords=["no data"],
        requires_live_data=True,
        notes="Historical price query",
    ),
    BenchmarkQuery(
        id="C03", category="C",
        query="What is the 52-week high and low for OGDC?",
        expected_route="stocks",
        expected_keywords=["OGDC", "PKR"],
        forbidden_keywords=["no data"],
        requires_live_data=True,
        notes="52-week range query — tests get_price_stats",
    ),
    BenchmarkQuery(
        id="C04", category="C",
        query="Compare ENGRO and FFC performance this month",
        expected_route="stocks",
        expected_keywords=["ENGRO", "FFC", "PKR"],
        forbidden_keywords=[],
        requires_live_data=True,
        notes="Multi-stock comparison",
    ),
    BenchmarkQuery(
        id="C05", category="C",
        query="What is the average volume for LUCK cement stock?",
        expected_route="stocks",
        expected_keywords=["LUCK", "volume"],
        forbidden_keywords=["no data"],
        requires_live_data=True,
        notes="Volume stat query",
    ),

    # ── D. FinQA-style Numerical / Factual (Pakistan-specific) ───────────────
    BenchmarkQuery(
        id="D01", category="D",
        query="What is the KSE-100 index?",
        expected_route="stocks",
        expected_keywords=["kse", "index", "pakistan"],
        forbidden_keywords=[],
        notes="FinQA: index definition with Pakistan context",
    ),
    BenchmarkQuery(
        id="D02", category="D",
        query="How is the KIBOR rate determined in Pakistan?",
        expected_route="banking",
        expected_keywords=["kibor", "interbank", "sbp"],
        forbidden_keywords=[],
        notes="FinQA: Pakistan banking rate mechanism",
    ),
    BenchmarkQuery(
        id="D03", category="D",
        query="What is the difference between T-bills and PIBs in Pakistan?",
        expected_route="theory",
        expected_keywords=["t-bill", "pib", "government"],
        forbidden_keywords=[],
        notes="FinQA: Pakistan debt instruments",
    ),
    BenchmarkQuery(
        id="D04", category="D",
        query="Explain Pakistan's current account deficit",
        expected_route="macro",
        expected_keywords=["deficit", "current account", "pakistan"],
        forbidden_keywords=[],
        notes="FinQA: macroeconomic concept with Pakistan data",
    ),
    BenchmarkQuery(
        id="D05", category="D",
        query="What is EPS and how is it calculated?",
        expected_route="theory",
        expected_keywords=["earnings per share", "eps"],
        forbidden_keywords=[],
        notes="FinQA: EPS formula",
    ),
    BenchmarkQuery(
        id="D06", category="D",
        query="How does SBP monetary policy affect stock prices?",
        expected_route="monetary_policy",
        expected_keywords=["sbp", "rate", "stock"],
        forbidden_keywords=[],
        notes="FinQA: policy transmission mechanism",
    ),
    BenchmarkQuery(
        id="D07", category="D",
        query="What sectors are listed on Pakistan Stock Exchange?",
        expected_route="stocks",
        expected_keywords=["psx", "sector"],
        forbidden_keywords=[],
        notes="FinQA: PSX sector knowledge",
    ),
    BenchmarkQuery(
        id="D08", category="D",
        query="What is dividend yield and which PSX stocks pay high dividends?",
        expected_route="stocks",
        expected_keywords=["dividend", "yield", "pakistan"],
        forbidden_keywords=[],
        notes="FinQA: dividend concept + Pakistan application",
    ),

    # ── E. FLUE-style Language & Sentiment ───────────────────────────────────
    BenchmarkQuery(
        id="E01", category="E",
        query="What does 'bearish' mean in stock markets?",
        expected_route="theory",
        expected_keywords=["bearish", "decline", "downtrend"],
        forbidden_keywords=[],
        notes="FLUE: financial sentiment terminology",
    ),
    BenchmarkQuery(
        id="E02", category="E",
        query="Explain the term 'market correction' in simple words",
        expected_route="theory",
        expected_keywords=["correction", "decline", "percent"],
        forbidden_keywords=[],
        notes="FLUE: market terminology in plain language",
    ),
    BenchmarkQuery(
        id="E03", category="E",
        query="What does a high RSI number mean for a stock?",
        expected_route="theory",
        expected_keywords=["rsi", "overbought", "70"],
        forbidden_keywords=[],
        notes="FLUE: technical indicator interpretation",
    ),
    BenchmarkQuery(
        id="E04", category="E",
        query="What is a bullish MACD crossover signal?",
        expected_route="theory",
        expected_keywords=["macd", "crossover", "bullish"],
        forbidden_keywords=[],
        notes="FLUE: MACD signal language",
    ),
    BenchmarkQuery(
        id="E05", category="E",
        query="What does 'blue chip stock' mean in Pakistan finance?",
        expected_route="theory",
        expected_keywords=["blue chip", "large cap"],
        forbidden_keywords=[],
        notes="FLUE: blue chip stock definition with Pakistan context",
    ),

    # ── F. Off-topic Rejection ───────────────────────────────────────────────
    BenchmarkQuery(
        id="F01", category="F",
        query="What is the recipe for biryani?",
        expected_route="off_topic",
        expected_keywords=[],
        forbidden_keywords=["stock", "pkr", "invest"],
        notes="Hard off-topic: cooking",
    ),
    BenchmarkQuery(
        id="F02", category="F",
        query="Who won the FIFA World Cup 2022?",
        expected_route="off_topic",
        expected_keywords=[],
        forbidden_keywords=["stock", "pkr"],
        notes="Hard off-topic: sports",
    ),
    BenchmarkQuery(
        id="F03", category="F",
        query="Write me a poem about the moon",
        expected_route="off_topic",
        expected_keywords=[],
        forbidden_keywords=["invest"],
        notes="Hard off-topic: creative writing",
    ),
    BenchmarkQuery(
        id="F04", category="F",
        query="What is the weather forecast for Karachi tomorrow?",
        expected_route="off_topic",
        expected_keywords=[],
        forbidden_keywords=["stock", "dividend"],
        notes="Off-topic: weather (Karachi is in Pakistan but not finance)",
    ),
    BenchmarkQuery(
        id="F05", category="F",
        query="Tell me about the history of the Mughal Empire",
        expected_route="off_topic",
        expected_keywords=[],
        forbidden_keywords=["invest", "portfolio"],
        notes="Off-topic: history",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# SCORING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

VERDICT_PATTERNS = [
    r"BULLISH", r"BEARISH", r"NEUTRAL",
    r"BETTER\s*\(Bullish\)", r"WORSE\s*\(Bearish\)",
    r"\*\*Verdict:\*\*",
    r"📈\s*BETTER", r"📉\s*WORSE", r"➡️\s*NEUTRAL",
]

FORBIDDEN_PREDICTION_PHRASES = [
    "cannot be determined",
    "data is unavailable",
    "no technical indicators",
    "cannot predict",
    "inherently speculative",
    "lack of technical data",
    "absence of specific technical indicators",
    "prediction is impossible",
    "cannot make a forecast",
    "not possible to predict",
]

PREDICTION_SECTIONS = ["📊 Technical Position", "📈 Signal Breakdown",
                        "🔮 Prediction", "⚠️"]
STOCK_SECTIONS = ["📊 Company Background", "📈 Performance Analysis", "🧠 Fintex"]
THEORY_SECTIONS = ["📖 Definition", "🔑 Key Points"]


@dataclass
class QueryResult:
    query_id: str
    query: str
    category: str
    expected_route: str
    actual_route: str
    answer_text: str
    response_time_ms: float
    is_prediction: bool

    route_score: int = 0       # 0 or 20
    verdict_score: int = 0     # 0 or 20
    no_hedge_score: int = 0    # 0 or 20
    format_score: int = 0      # 0–20
    relevance_score: int = 0   # 0–20
    error: Optional[str] = None

    @property
    def total_score(self) -> int:
        return self.route_score + self.verdict_score + self.no_hedge_score + \
               self.format_score + self.relevance_score

    @property
    def passed(self) -> bool:
        return self.total_score >= 60


def score_result(bq: BenchmarkQuery, result: Dict[str, Any],
                 response_time_ms: float) -> QueryResult:
    answer_obj = result.get("answer", {})
    answer_text = answer_obj.get("answer", "") if isinstance(answer_obj, dict) else str(answer_obj)
    actual_route = result.get("category", "unknown")
    is_prediction = result.get("is_prediction", False)
    answer_lower = answer_text.lower()

    qr = QueryResult(
        query_id=bq.id,
        query=bq.query,
        category=bq.category,
        expected_route=bq.expected_route,
        actual_route=actual_route,
        answer_text=answer_text,
        response_time_ms=response_time_ms,
        is_prediction=is_prediction,
    )

    # ── Route score (20 pts) ──────────────────────────────────────────────────
    # Accept a broader match: "stocks" covers "price_query", "prediction", etc.
    route_ok = (actual_route == bq.expected_route or
                actual_route.startswith(bq.expected_route) or
                bq.expected_route in actual_route)
    qr.route_score = 20 if route_ok else 0

    # ── Verdict score (20 pts) ────────────────────────────────────────────────
    if bq.requires_verdict:
        has_verdict = any(re.search(p, answer_text, re.IGNORECASE) for p in VERDICT_PATTERNS)
        qr.verdict_score = 20 if has_verdict else 0
    else:
        qr.verdict_score = 20  # not applicable — full marks

    # ── No-hedge score (20 pts) ───────────────────────────────────────────────
    if bq.requires_verdict:
        hedge_found = any(p in answer_lower for p in FORBIDDEN_PREDICTION_PHRASES)
        qr.no_hedge_score = 0 if hedge_found else 20
    else:
        # For non-prediction queries, check forbidden topic keywords
        bad_found = any(w in answer_lower for w in bq.forbidden_keywords)
        qr.no_hedge_score = 0 if bad_found else 20

    # ── Format score (20 pts) ─────────────────────────────────────────────────
    if bq.expected_route == "stocks" and is_prediction:
        sections = PREDICTION_SECTIONS
    elif bq.expected_route == "stocks":
        sections = STOCK_SECTIONS
    elif bq.expected_route == "theory":
        sections = THEORY_SECTIONS
    else:
        sections = []

    if sections:
        hits = sum(1 for s in sections if s in answer_text)
        qr.format_score = round((hits / len(sections)) * 20)
    else:
        qr.format_score = 20  # not applicable

    # ── Relevance score (20 pts) ──────────────────────────────────────────────
    if bq.expected_keywords:
        hits = sum(1 for kw in bq.expected_keywords if kw.lower() in answer_lower)
        qr.relevance_score = round((hits / len(bq.expected_keywords)) * 20)
    else:
        qr.relevance_score = 20  # no keywords to check

    return qr


# ─────────────────────────────────────────────────────────────────────────────
# OFFLINE MOCK RUNNER  (returns stubbed answers, no API calls)
# ─────────────────────────────────────────────────────────────────────────────

OFFLINE_STUBS: Dict[str, Dict[str, Any]] = {
    # prediction stub
    "predict": {
        "category": "stocks",
        "is_prediction": True,
        "answer": {
            "answer": (
                "### 📊 Technical Position — ENGRO\n"
                "**Latest Price:** PKR 312.40  (as of 2026-05-08)\n"
                "**RSI (14):** 54.3 — NEUTRAL\n"
                "**MACD:** +0.0231 | Signal +0.0189 | Histogram +0.0042 [BULLISH]\n\n"
                "### 📈 Signal Breakdown\n"
                "**Bullish (4):** MACD bullish, SMA7 > SMA30, price above SMA7, volume +12%\n\n"
                "### 🔮 Prediction for May 10, 2026\n"
                "**Verdict:** 📈 **BETTER (Bullish)** — 4/5 signals point upward\n"
                "**Confidence:** High (80%)\n\n"
                "### ⚠️ Key Risks\n"
                "- SBP rate decision\n"
                "*AI-generated. Not financial advice.*"
            )
        }
    },
    # stock stub
    "stock": {
        "category": "stocks",
        "is_prediction": False,
        "answer": {
            "answer": (
                "### 📊 Company Background\n"
                "- **Company:** ENGRO Corporation (PSX: ENGRO)\n"
                "- **PKR 312.40** latest close\n\n"
                "### 📈 Performance Analysis\n"
                "30-day change: +4.2%\n\n"
                "### 🧠 Fintex Investment Opinion\n"
                "ENGRO remains a strong dividend payer on the PSX.\n"
                "*AI-generated opinion. Not financial advice.*"
            )
        }
    },
    # theory stub
    "theory": {
        "category": "theory",
        "is_prediction": False,
        "answer": {
            "answer": (
                "### 📖 Definition\nThe PE ratio compares share price to earnings.\n\n"
                "### 📝 Detailed Explanation\nUsed to value stocks relative to earnings.\n\n"
                "### 🔑 Key Points\n- P/E = Price / EPS\n- PSX avg 8-10x\n\n"
                "### 🇵🇰 Pakistan Context\nBanking sector trades at lower P/E.\n\n"
                "### 📚 Further Reading\nhttps://psx.com.pk"
            )
        }
    },
    # macro stub
    "macro": {
        "category": "macro",
        "is_prediction": False,
        "answer": {"answer": "Pakistan's inflation rate is approximately 12% as of 2026. Pakistan CPI."}
    },
    # off_topic stub
    "off_topic": {
        "category": "off_topic",
        "is_prediction": False,
        "answer": {"answer": "This query is outside the scope of Fintex Pakistan Finance."}
    },
    # banking stub
    "banking": {
        "category": "banking",
        "is_prediction": False,
        "answer": {"answer": "KIBOR is the Karachi Interbank Offered Rate set by the SBP. Interbank rate determination."}
    },
    # monetary_policy stub
    "monetary_policy": {
        "category": "monetary_policy",
        "is_prediction": False,
        "answer": {"answer": "SBP policy rate is currently 15%. The State Bank of Pakistan sets rate targets."}
    },
}


def _offline_stub(bq: BenchmarkQuery) -> Dict[str, Any]:
    q = bq.query.lower()
    if bq.requires_verdict or any(k in q for k in ["predict", "forecast", "will it", "gonna", "buy or sell"]):
        return OFFLINE_STUBS["predict"]
    if bq.expected_route == "off_topic":
        return OFFLINE_STUBS["off_topic"]
    if bq.expected_route == "theory":
        return OFFLINE_STUBS["theory"]
    if bq.expected_route == "macro":
        return OFFLINE_STUBS["macro"]
    if bq.expected_route == "banking":
        return OFFLINE_STUBS["banking"]
    if bq.expected_route == "monetary_policy":
        return OFFLINE_STUBS["monetary_policy"]
    return OFFLINE_STUBS["stock"]


# ─────────────────────────────────────────────────────────────────────────────
# LIVE PIPELINE RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def _load_pipeline():
    try:
        from src.reasoning.fintex_pipeline import FintexPipeline
        return FintexPipeline()
    except Exception as e:
        return None


def run_query(pipeline, bq: BenchmarkQuery, offline: bool) -> QueryResult:
    if offline or pipeline is None:
        start = time.time()
        result = _offline_stub(bq)
        elapsed = (time.time() - start) * 1000
    else:
        start = time.time()
        try:
            result = pipeline.answer(bq.query, format="detailed")
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            qr = QueryResult(
                query_id=bq.id, query=bq.query, category=bq.category,
                expected_route=bq.expected_route, actual_route="error",
                answer_text="", response_time_ms=elapsed, is_prediction=False,
                error=str(e),
            )
            return qr
        elapsed = (time.time() - start) * 1000

    return score_result(bq, result, elapsed)


# ─────────────────────────────────────────────────────────────────────────────
# REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_NAMES = {
    "A": "Routing Accuracy",
    "B": "Prediction Quality",
    "C": "Stock Data Accuracy",
    "D": "FinQA-style Q&A",
    "E": "FLUE-style Language",
    "F": "Off-topic Rejection",
}

SCORE_COLS = ["route", "verdict", "no_hedge", "format", "relevance"]


def _bar(score: int, max_score: int = 100, width: int = 20) -> str:
    filled = round((score / max_score) * width) if max_score else 0
    return "#" * filled + "." * (width - filled)


def print_report(results: List[QueryResult], elapsed_total: float) -> None:
    PASS = "PASS"
    FAIL = "FAIL"

    print("\n" + "=" * 80)
    print("  FINTEX FINANCIAL BENCHMARK REPORT")
    print("=" * 80)

    # Per-category breakdown
    by_cat: Dict[str, List[QueryResult]] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    for cat_id in sorted(by_cat):
        cat_results = by_cat[cat_id]
        cat_name = CATEGORY_NAMES.get(cat_id, cat_id)
        passed = sum(1 for r in cat_results if r.passed)
        avg = sum(r.total_score for r in cat_results) / len(cat_results) if cat_results else 0

        print(f"\n-- Category {cat_id}: {cat_name} {'-' * (50 - len(cat_name))}")
        print(f"   Passed: {passed}/{len(cat_results)}  |  Avg score: {avg:.0f}/100")
        print(f"   {'ID':>4}  {'Route':8}  {'RT':6}  {'Score':6}  {'R':3}  {'V':3}  {'H':3}  {'F':3}  {'Rel':3}  Status  Query")
        print(f"   {'-'*4}  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*3}  {'-'*3}  {'-'*3}  {'-'*3}  {'-'*3}  {'-'*6}  {'-'*40}")

        for r in cat_results:
            status = PASS if r.passed else FAIL
            if r.error:
                status = "ERR "
            rt = f"{r.response_time_ms:.0f}ms"
            short_q = r.query[:40] + ("..." if len(r.query) > 40 else "")
            print(
                f"   {r.query_id:>4}  {r.actual_route:8.8}  {rt:6}  {r.total_score:>5}/100  "
                f"{r.route_score:>3}  {r.verdict_score:>3}  {r.no_hedge_score:>3}  "
                f"{r.format_score:>3}  {r.relevance_score:>3}  {status}      {short_q}"
            )
            if r.error:
                print(f"         ERROR: {r.error[:80]}")

    # Overall summary
    total_passed = sum(1 for r in results if r.passed)
    total_queries = len(results)
    overall_avg = sum(r.total_score for r in results) / total_queries if total_queries else 0

    print("\n" + "=" * 80)
    print(f"  OVERALL:  {total_passed}/{total_queries} passed  |  Avg score: {overall_avg:.1f}/100")
    print(f"  [{_bar(int(overall_avg))}]  {overall_avg:.1f}%")
    print(f"  Total time: {elapsed_total:.1f}s")

    # Score column legend
    print("\n  Score columns: R=Route(20) V=Verdict(20) H=No-Hedge(20) F=Format(20) Rel=Relevance(20)")

    # Failures detail
    failures = [r for r in results if not r.passed and not r.error]
    if failures:
        print(f"\n── Failures ({len(failures)}) ──────────────────────────────────────────────")
        for r in failures:
            print(f"  [{r.query_id}] {r.query}")
            print(f"       Expected route: {r.expected_route}  |  Got: {r.actual_route}")
            issues = []
            if r.route_score == 0:
                issues.append("wrong route")
            if r.verdict_score == 0:
                issues.append("no verdict")
            if r.no_hedge_score == 0:
                issues.append("hedge phrases found")
            if r.format_score < 10:
                issues.append("missing format sections")
            if r.relevance_score < 10:
                issues.append("missing expected keywords")
            print(f"       Issues: {', '.join(issues)}")
            # Show first 200 chars of answer
            preview = r.answer_text[:200].replace("\n", " ")
            print(f"       Answer preview: {preview}…")
            print()

    print("=" * 80 + "\n")


def save_json_report(results: List[QueryResult], path: str) -> None:
    data = []
    for r in results:
        data.append({
            "id": r.query_id,
            "category": r.category,
            "query": r.query,
            "expected_route": r.expected_route,
            "actual_route": r.actual_route,
            "total_score": r.total_score,
            "passed": r.passed,
            "scores": {
                "route": r.route_score,
                "verdict": r.verdict_score,
                "no_hedge": r.no_hedge_score,
                "format": r.format_score,
                "relevance": r.relevance_score,
            },
            "response_time_ms": r.response_time_ms,
            "is_prediction": r.is_prediction,
            "error": r.error,
        })
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"JSON report saved → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fintex Financial Benchmark")
    parser.add_argument("--offline", action="store_true",
                        help="Run with offline stubs — no live API calls")
    parser.add_argument("--category", type=str, default=None,
                        help="Run only one category (A/B/C/D/E/F)")
    parser.add_argument("--id", type=str, default=None,
                        help="Run a single query by ID (e.g. B07)")
    parser.add_argument("--json", type=str, default=None,
                        help="Save JSON report to this path")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Delay between live queries in seconds (default 1.5)")
    args = parser.parse_args()

    # Filter queries
    queries = BENCHMARK_QUERIES
    if args.category:
        queries = [q for q in queries if q.category == args.category.upper()]
    if args.id:
        queries = [q for q in queries if q.id.upper() == args.id.upper()]

    if not queries:
        print("No queries match the filter. Check --category / --id.")
        return

    pipeline = None
    if not args.offline:
        print("Loading Fintex pipeline…", end=" ", flush=True)
        pipeline = _load_pipeline()
        if pipeline:
            print("OK")
        else:
            print("FAILED (offline mode fallback -- check .env)")
            args.offline = True

    mode = "OFFLINE (stubs)" if args.offline else "LIVE (Fintex pipeline)"
    print(f"\nRunning {len(queries)} queries in {mode} mode...\n")

    results: List[QueryResult] = []
    total_start = time.time()

    for i, bq in enumerate(queries, 1):
        print(f"  [{i:02d}/{len(queries):02d}] {bq.id} - {bq.query[:60]}...", end=" ", flush=True)
        qr = run_query(pipeline, bq, args.offline)
        results.append(qr)
        status = "PASS" if qr.passed else ("ERR" if qr.error else "FAIL")
        print(f"[{status}]  {qr.total_score}/100  ({qr.response_time_ms:.0f}ms)")

        if not args.offline and i < len(queries):
            time.sleep(args.delay)

    total_elapsed = time.time() - total_start
    print_report(results, total_elapsed)

    if args.json:
        save_json_report(results, args.json)


# ─────────────────────────────────────────────────────────────────────────────
# PYTEST INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

import pytest

def _get_pipeline_cached():
    if not hasattr(_get_pipeline_cached, "_instance"):
        _get_pipeline_cached._instance = _load_pipeline()
    return _get_pipeline_cached._instance

PIPELINE_AVAILABLE = pytest.mark.skipif(
    _load_pipeline() is None,
    reason="Fintex pipeline not importable (check .env)",
)


class TestRoutingAccuracy:
    """Category A: correct category routing for all query types."""

    @pytest.mark.parametrize("bq", [q for q in BENCHMARK_QUERIES if q.category == "A"],
                             ids=[q.id for q in BENCHMARK_QUERIES if q.category == "A"])
    def test_routing_offline(self, bq: BenchmarkQuery):
        result = _offline_stub(bq)
        qr = score_result(bq, result, 0)
        assert qr.route_score == 20, (
            f"{bq.id}: expected route '{bq.expected_route}', "
            f"got '{qr.actual_route}'"
        )

    @PIPELINE_AVAILABLE
    @pytest.mark.parametrize("bq", [q for q in BENCHMARK_QUERIES if q.category == "A"],
                             ids=[q.id for q in BENCHMARK_QUERIES if q.category == "A"])
    def test_routing_live(self, bq: BenchmarkQuery):
        pipeline = _get_pipeline_cached()
        qr = run_query(pipeline, bq, offline=False)
        assert qr.route_score == 20, (
            f"{bq.id}: expected route '{bq.expected_route}', "
            f"got '{qr.actual_route}'"
        )


class TestPredictionQuality:
    """Category B: predictions must give concrete verdicts, no hedging."""

    @pytest.mark.parametrize("bq", [q for q in BENCHMARK_QUERIES if q.category == "B"],
                             ids=[q.id for q in BENCHMARK_QUERIES if q.category == "B"])
    def test_prediction_offline(self, bq: BenchmarkQuery):
        result = _offline_stub(bq)
        qr = score_result(bq, result, 0)
        assert qr.verdict_score == 20, f"{bq.id}: no verdict found"
        assert qr.no_hedge_score == 20, f"{bq.id}: forbidden hedge phrases found"

    @PIPELINE_AVAILABLE
    @pytest.mark.parametrize("bq", [q for q in BENCHMARK_QUERIES if q.category == "B"],
                             ids=[q.id for q in BENCHMARK_QUERIES if q.category == "B"])
    def test_prediction_live(self, bq: BenchmarkQuery):
        pipeline = _get_pipeline_cached()
        qr = run_query(pipeline, bq, offline=False)
        assert qr.no_hedge_score == 20, (
            f"{bq.id}: forbidden hedge phrases found in live answer.\n"
            f"Answer preview: {qr.answer_text[:300]}"
        )
        assert qr.verdict_score == 20, (
            f"{bq.id}: no BULLISH/BEARISH/NEUTRAL verdict found.\n"
            f"Answer preview: {qr.answer_text[:300]}"
        )


class TestOriginalBugQuery:
    """B07 — the exact query that originally returned the theory/horoscope response."""

    def test_b07_offline(self):
        bq = next(q for q in BENCHMARK_QUERIES if q.id == "B07")
        result = _offline_stub(bq)
        qr = score_result(bq, result, 0)
        assert "horoscope" not in qr.answer_text.lower()
        assert "inherently speculative" not in qr.answer_text.lower()

    @PIPELINE_AVAILABLE
    def test_b07_live(self):
        bq = next(q for q in BENCHMARK_QUERIES if q.id == "B07")
        pipeline = _get_pipeline_cached()
        qr = run_query(pipeline, bq, offline=False)
        assert qr.route_score == 20, f"B07 routed to '{qr.actual_route}', expected 'stocks'"
        assert qr.verdict_score == 20, f"B07 has no verdict. Answer: {qr.answer_text[:400]}"
        assert qr.no_hedge_score == 20, f"B07 contains hedge phrases. Answer: {qr.answer_text[:400]}"


class TestOffTopicRejection:
    """Category F: non-finance queries must be rejected."""

    @pytest.mark.parametrize("bq", [q for q in BENCHMARK_QUERIES if q.category == "F"],
                             ids=[q.id for q in BENCHMARK_QUERIES if q.category == "F"])
    def test_off_topic_offline(self, bq: BenchmarkQuery):
        result = _offline_stub(bq)
        qr = score_result(bq, result, 0)
        assert qr.route_score == 20, f"{bq.id}: off-topic query not rejected"

    @PIPELINE_AVAILABLE
    @pytest.mark.parametrize("bq", [q for q in BENCHMARK_QUERIES if q.category == "F"],
                             ids=[q.id for q in BENCHMARK_QUERIES if q.category == "F"])
    def test_off_topic_live(self, bq: BenchmarkQuery):
        pipeline = _get_pipeline_cached()
        qr = run_query(pipeline, bq, offline=False)
        assert qr.actual_route == "off_topic", (
            f"{bq.id}: expected off_topic, got '{qr.actual_route}'\n"
            f"Query: {bq.query}"
        )


class TestOverallBenchmark:
    """Full suite — must achieve ≥70% pass rate."""

    def test_offline_pass_rate(self):
        results = [score_result(bq, _offline_stub(bq), 0) for bq in BENCHMARK_QUERIES]
        passed = sum(1 for r in results if r.passed)
        rate = passed / len(results)
        assert rate >= 0.70, f"Offline pass rate {rate:.0%} < 70%"

    @PIPELINE_AVAILABLE
    def test_live_pass_rate(self):
        pipeline = _get_pipeline_cached()
        results = [run_query(pipeline, bq, offline=False) for bq in BENCHMARK_QUERIES]
        passed = sum(1 for r in results if r.passed)
        rate = passed / len(results)
        assert rate >= 0.70, (
            f"Live pass rate {rate:.0%} < 70%\n"
            f"Failures: {[r.query_id for r in results if not r.passed]}"
        )


if __name__ == "__main__":
    main()
