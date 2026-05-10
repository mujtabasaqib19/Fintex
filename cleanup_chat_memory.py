"""
Cleanup: delete all chat_memory entries from Qdrant + Supabase chunks.

These are old Q&A pairs saved by _save_to_qdrant() that pollute vector search
results with stale or bad answers.

What is deleted:
  - Qdrant: all points where payload.source_type == "chat_memory"
  - Supabase chunks: rows whose IDs match those Qdrant points

What is NOT touched:
  - Any Qdrant point with source_type != "chat_memory"
  - Supabase documents, stocks, messages, or any other table

Run:  python cleanup_chat_memory.py
      python cleanup_chat_memory.py --dry-run   (inspect without deleting)
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from qdrant_client.models import (
    Filter, FieldCondition, MatchValue,
    FilterSelector,
)

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true", help="Print what would be deleted without actually deleting")
args = parser.parse_args()

DRY_RUN = args.dry_run

print("=" * 60)
print("Fintex chat_memory cleanup")
print("DRY RUN mode:", DRY_RUN)
print("=" * 60)

# ── Connect ───────────────────────────────────────────────────────────────────
print("\n[1] Connecting to Qdrant and Supabase...")
from src.db.qdrant_client import get_qdrant_client
from src.db.connection import get_supabase_client
from config.settings import get_settings

settings = get_settings()
qdrant = get_qdrant_client()
supabase = get_supabase_client()
collection = settings.qdrant_collection
print(f"    Qdrant collection: {collection}")

# ── Count before ─────────────────────────────────────────────────────────────
print("\n[2] Counting chat_memory points in Qdrant...")
chat_memory_filter = Filter(
    must=[FieldCondition(key="source_type", match=MatchValue(value="chat_memory"))]
)

# Scroll to collect all matching IDs (handles pagination automatically)
all_ids = []
offset = None
PAGE = 100

while True:
    result = qdrant.scroll(
        collection_name=collection,
        scroll_filter=chat_memory_filter,
        limit=PAGE,
        offset=offset,
        with_payload=False,
        with_vectors=False,
    )
    points, next_offset = result
    all_ids.extend(str(p.id) for p in points)
    if next_offset is None:
        break
    offset = next_offset

print(f"    Found {len(all_ids)} chat_memory points")

if not all_ids:
    print("\nNothing to delete. Exiting.")
    sys.exit(0)

# ── Preview ───────────────────────────────────────────────────────────────────
print(f"\n[3] First 5 IDs that will be removed:")
for id_ in all_ids[:5]:
    print(f"    {id_}")
if len(all_ids) > 5:
    print(f"    ... and {len(all_ids) - 5} more")

# ── Delete from Qdrant ────────────────────────────────────────────────────────
if not DRY_RUN:
    print(f"\n[4] Deleting {len(all_ids)} points from Qdrant (filter-based)...")
    qdrant.delete(
        collection_name=collection,
        points_selector=FilterSelector(filter=chat_memory_filter),
    )
    print("    Qdrant delete: done")
else:
    print(f"\n[4] DRY RUN — would delete {len(all_ids)} Qdrant points")

# ── Delete from Supabase chunks ───────────────────────────────────────────────
BATCH = 50
total_sb = 0

if not DRY_RUN:
    print(f"\n[5] Deleting matching rows from Supabase 'chunks' table (in batches of {BATCH})...")
    for i in range(0, len(all_ids), BATCH):
        batch = all_ids[i : i + BATCH]
        resp = supabase.table("chunks").delete().in_("id", batch).execute()
        count = len(resp.data) if resp.data else 0
        total_sb += count
        print(f"    Batch {i//BATCH + 1}: deleted {count} rows")
    print(f"    Supabase delete: {total_sb} rows removed")
else:
    print(f"\n[5] DRY RUN — would delete up to {len(all_ids)} rows from Supabase 'chunks'")

# ── Verify ────────────────────────────────────────────────────────────────────
if not DRY_RUN:
    print("\n[6] Verifying — scanning for remaining chat_memory points...")
    verify, _ = qdrant.scroll(
        collection_name=collection,
        scroll_filter=chat_memory_filter,
        limit=10,
        with_payload=False,
        with_vectors=False,
    )
    remaining = len(verify)
    if remaining == 0:
        print("    CLEAN — 0 chat_memory points remain in Qdrant")
    else:
        print(f"    WARNING: {remaining} chat_memory points still found (retry?)")

print("\n" + "=" * 60)
if DRY_RUN:
    print(f"DRY RUN complete. Would have removed {len(all_ids)} entries.")
    print("Re-run without --dry-run to actually delete.")
else:
    print(f"Cleanup complete. Removed {len(all_ids)} Qdrant points and {total_sb} Supabase rows.")
print("=" * 60)
