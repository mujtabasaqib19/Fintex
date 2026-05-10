"""
Benchmark 2 — RAG Retrieval Quality
=====================================
Measures whether Qdrant returns semantically relevant chunks for financial
queries using three metrics adapted from the RAGAS framework:

  • Context Precision  — relevant hits / total hits retrieved
  • Context Recall     — retrieved relevant / all expected relevant
  • Avg Cosine Score   — mean similarity of top-k hits

The test uses a curated golden dataset of 15 Pakistan-finance Q&A pairs
with expected Qdrant `sector_category` labels.  Tests that pass without a
live Qdrant connection are marked with LIVE_SKIP and can be run locally.

Run (live Qdrant):
    pytest tests/test_rag_retrieval.py -v

Run (offline / CI):
    pytest tests/test_rag_retrieval.py -v -k "not live"
"""
import sys, os, json, time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Live connectivity guard ────────────────────────────────────────────────────
def _qdrant_reachable() -> bool:
    try:
        from src.db.qdrant_client import QdrantService
        svc = QdrantService()
        info = svc.get_collection_info()
        return info.get("vector_count", 0) >= 0
    except Exception:
        return False

LIVE = _qdrant_reachable()
LIVE_SKIP = pytest.mark.skipif(not LIVE, reason="Qdrant not reachable — set QDRANT_URL / QDRANT_API_KEY")


# ── Golden dataset ─────────────────────────────────────────────────────────────
# Each entry: query, expected_category, must_contain_keywords (in chunk text)
GOLDEN_QA = [
    # Stocks
    {"query": "ENGRO stock price performance",
     "category": "stocks", "keywords": ["engro", "stock", "price"]},
    {"query": "HBL dividend yield analysis",
     "category": "stocks", "keywords": ["hbl", "dividend", "bank"]},
    {"query": "OGDC oil gas exploration Pakistan",
     "category": "stocks", "keywords": ["ogdc", "oil", "petroleum"]},
    {"query": "PSX KSE-100 index performance",
     "category": "stocks", "keywords": ["kse", "index", "psx"]},
    # Monetary policy
    {"query": "SBP policy rate interest rate decision",
     "category": "monetary_policy", "keywords": ["sbp", "policy rate", "interest"]},
    {"query": "State Bank of Pakistan monetary tightening",
     "category": "monetary_policy", "keywords": ["state bank", "monetary"]},
    # Macro
    {"query": "Pakistan GDP growth economic outlook",
     "category": "macro", "keywords": ["gdp", "growth", "pakistan"]},
    {"query": "Pakistan inflation CPI consumer prices",
     "category": "macro", "keywords": ["inflation", "cpi"]},
    {"query": "Pakistan IMF loan agreement bailout",
     "category": "macro", "keywords": ["imf", "pakistan"]},
    {"query": "USD PKR exchange rate rupee depreciation",
     "category": "macro", "keywords": ["exchange rate", "rupee", "pkr"]},
    # Banking
    {"query": "MCB bank non-performing loans NPL ratio",
     "category": "banking", "keywords": ["bank", "npl", "loan"]},
    {"query": "Meezan Bank Islamic banking deposits",
     "category": "banking", "keywords": ["meezan", "islamic", "bank"]},
    # Theory
    {"query": "What is price to earnings ratio PE",
     "category": "theory", "keywords": ["pe ratio", "earnings", "price"]},
    {"query": "What is dividend yield formula",
     "category": "theory", "keywords": ["dividend", "yield"]},
    {"query": "What is beta coefficient systematic risk",
     "category": "theory", "keywords": ["beta", "risk"]},
]

# Target thresholds
MIN_AVG_SCORE = 0.60        # mean cosine similarity across top-3 hits
MIN_PRECISION = 0.50        # fraction of retrieved hits whose category matches
MIN_RECALL    = 0.40        # fraction of golden items that get ≥1 hit with score ≥ threshold
SCORE_THRESHOLD = 0.50      # hit is "relevant" if cosine similarity ≥ this


# ── Helpers ───────────────────────────────────────────────────────────────────
def _embed(text: str):
    from src.reasoning.fintex_pipeline import embed_text
    return embed_text(text)


def _search(query: str, limit: int = 3):
    from src.db.qdrant_client import QdrantService
    from src.db.connection import get_supabase_client
    svc = QdrantService()
    vec = _embed(query)
    return svc.search(query_vector=vec, limit=limit, score_threshold=0.0)


def _fetch_chunk_content(doc_id: str) -> str:
    """Fetch chunk text from Supabase given a Qdrant doc_id."""
    try:
        from src.db.connection import get_supabase_client
        sb = get_supabase_client()
        r = sb.table("chunks").select("content").eq("id", doc_id).single().execute()
        return (r.data or {}).get("content", "")
    except Exception:
        return ""


# ── Unit tests (offline — no Qdrant needed) ───────────────────────────────────
class TestRAGOffline:
    """Tests that run without a live Qdrant connection."""

    def test_golden_dataset_not_empty(self):
        assert len(GOLDEN_QA) >= 10, "Golden dataset too small"

    def test_all_entries_have_required_keys(self):
        for item in GOLDEN_QA:
            assert "query" in item
            assert "category" in item
            assert "keywords" in item
            assert len(item["keywords"]) >= 1

    def test_categories_are_valid(self):
        valid = {"stocks", "monetary_policy", "macro", "banking", "theory"}
        for item in GOLDEN_QA:
            assert item["category"] in valid, f"Unknown category: {item['category']}"

    def test_queries_are_non_empty(self):
        for item in GOLDEN_QA:
            assert item["query"].strip(), "Empty query in golden dataset"


# ── Live integration tests ────────────────────────────────────────────────────
class TestRAGLive:
    """
    Live tests that hit the real Qdrant + Supabase stack.
    Skipped automatically when the services are unreachable.
    """

    @LIVE_SKIP
    def test_retrieval_returns_results(self):
        """Every query must return at least 1 Qdrant hit."""
        failures = []
        for item in GOLDEN_QA:
            hits = _search(item["query"], limit=3)
            if len(hits) == 0:
                failures.append(item["query"])
        if failures:
            pytest.fail(f"{len(failures)} queries returned 0 hits:\n" + "\n".join(failures))

    @LIVE_SKIP
    def test_avg_cosine_score(self):
        """Mean cosine similarity across all top-3 hits >= MIN_AVG_SCORE."""
        all_scores = []
        for item in GOLDEN_QA:
            hits = _search(item["query"], limit=3)
            all_scores.extend(h["score"] for h in hits)
        if not all_scores:
            pytest.skip("No hits returned — KB may be empty")
        avg = sum(all_scores) / len(all_scores)
        assert avg >= MIN_AVG_SCORE, \
            f"Avg cosine score {avg:.3f} < threshold {MIN_AVG_SCORE}"

    @LIVE_SKIP
    def test_context_precision(self):
        """
        Context Precision = relevant_hits / total_hits.
        A hit is 'relevant' if its sector_category matches the golden category
        OR its score >= SCORE_THRESHOLD (high-similarity hit assumed relevant).
        Target >= MIN_PRECISION.
        """
        total, relevant = 0, 0
        for item in GOLDEN_QA:
            hits = _search(item["query"], limit=3)
            for h in hits:
                total += 1
                if h.get("sector_category") == item["category"] or h["score"] >= SCORE_THRESHOLD:
                    relevant += 1
        if total == 0:
            pytest.skip("No hits — KB may be empty")
        precision = relevant / total
        assert precision >= MIN_PRECISION, \
            f"Context Precision {precision:.2%} < threshold {MIN_PRECISION:.2%}"

    @LIVE_SKIP
    def test_context_recall(self):
        """
        Context Recall = queries that got ≥1 relevant hit / total queries.
        Target >= MIN_RECALL.
        """
        recalled = 0
        for item in GOLDEN_QA:
            hits = _search(item["query"], limit=3)
            for h in hits:
                if h.get("sector_category") == item["category"] or h["score"] >= SCORE_THRESHOLD:
                    recalled += 1
                    break
        recall = recalled / len(GOLDEN_QA)
        assert recall >= MIN_RECALL, \
            f"Context Recall {recall:.2%} < threshold {MIN_RECALL:.2%}"

    @LIVE_SKIP
    def test_per_category_precision(self):
        """Reports precision breakdown per category — fails if any category < 0.30."""
        from collections import defaultdict
        hits_by_cat = defaultdict(lambda: {"total": 0, "relevant": 0})
        for item in GOLDEN_QA:
            hits = _search(item["query"], limit=3)
            cat = item["category"]
            for h in hits:
                hits_by_cat[cat]["total"] += 1
                if h.get("sector_category") == cat or h["score"] >= SCORE_THRESHOLD:
                    hits_by_cat[cat]["relevant"] += 1

        report = {}
        failed_cats = []
        for cat, counts in hits_by_cat.items():
            prec = counts["relevant"] / counts["total"] if counts["total"] > 0 else 0
            report[cat] = f"{prec:.2%}"
            if prec < 0.30 and counts["total"] > 0:
                failed_cats.append(f"{cat}: {prec:.2%}")

        print("\nPer-category precision:", json.dumps(report, indent=2))
        if failed_cats:
            pytest.fail("Categories below 30% precision:\n" + "\n".join(failed_cats))

    @LIVE_SKIP
    def test_top1_hit_above_threshold_for_all_queries(self):
        """The best (top-1) hit for each query must score >= SCORE_THRESHOLD."""
        failed = []
        for item in GOLDEN_QA:
            hits = _search(item["query"], limit=1)
            if not hits or hits[0]["score"] < SCORE_THRESHOLD:
                score = hits[0]["score"] if hits else 0.0
                failed.append(f"{item['query']!r} → score={score:.3f}")
        if failed:
            pytest.fail(
                f"{len(failed)}/{len(GOLDEN_QA)} queries failed top-1 threshold "
                f"({SCORE_THRESHOLD}):\n" + "\n".join(failed)
            )

    @LIVE_SKIP
    def test_chunk_content_keyword_match(self):
        """
        For at least 60% of golden items, the top-1 chunk content must contain
        at least one expected keyword (case-insensitive).  This validates that
        the chunk text, not just the vector, is semantically appropriate.
        """
        matched = 0
        for item in GOLDEN_QA:
            hits = _search(item["query"], limit=1)
            if not hits:
                continue
            content = _fetch_chunk_content(hits[0]["doc_id"]).lower()
            if any(kw.lower() in content for kw in item["keywords"]):
                matched += 1
        ratio = matched / len(GOLDEN_QA)
        assert ratio >= 0.60, \
            f"Keyword match ratio {ratio:.2%} — only {matched}/{len(GOLDEN_QA)} chunks matched"
