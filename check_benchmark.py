"""
Quick check: fire one query through the live pipeline and verify
the benchmark result was saved to Supabase.

Run:  python check_benchmark.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

print("1. Loading pipeline...")
from src.reasoning.fintex_pipeline import FintexPipeline
pipeline = FintexPipeline()
print("   OK")

print("2. Running test query: 'predict if ENGRO gonna perform better on may 10'")
result = pipeline.answer("predict if ENGRO gonna perform better on may 10")
print(f"   category={result.get('category')} is_prediction={result.get('is_prediction')}")
print(f"   score source={result.get('source')}")

print("3. Waiting 2s for background thread to save...")
time.sleep(2)

print("4. Reading latest benchmark row from Supabase...")
from src.db.connection import get_supabase_client
sb = get_supabase_client()
rows = (
    sb.table("benchmark_results")
    .select("query, category, total_score, passed, verdict_score, no_hedge_score, created_at")
    .order("created_at", desc=True)
    .limit(1)
    .execute()
).data

if rows:
    r = rows[0]
    print(f"\n   SAVED - score={r['total_score']}/100  passed={r['passed']}")
    print(f"   query:         {r['query']}")
    print(f"   category:      {r['category']}")
    print(f"   verdict_score: {r['verdict_score']}/20")
    print(f"   no_hedge:      {r['no_hedge_score']}/20")
    print(f"   created_at:    {r['created_at']}")
    print("\n   Benchmark tracking is WORKING.")
else:
    print("\n   No rows found. Check:")
    print("   - Did you run supabase/benchmark_results.sql in the Supabase SQL editor?")
    print("   - Any error printed above from the background thread?")
