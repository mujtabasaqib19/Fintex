import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.db.qdrant_client import QdrantService
from qdrant_client.models import PayloadSchemaType

def fix():
    try:
        service = QdrantService()
        collection = service.collection_name
        print(f"Adding indexes to {collection}...")
        service.client.create_payload_index(
            collection_name=collection,
            field_name="sector_category",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        service.client.create_payload_index(
            collection_name=collection,
            field_name="source_type",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix()
