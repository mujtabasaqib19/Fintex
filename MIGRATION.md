# Migration Summary: OpenAI → Gemini + Qdrant

## Changes Made

### 1. AI Model Migration
- **Before**: OpenAI GPT-4 + text-embedding-3-small
- **After**: Google Gemini 2.0 Flash + embedding-001

### 2. Vector Database Migration
- **Before**: Embeddings stored in Supabase using pgvector
- **After**: Embeddings stored in Qdrant vector database

### 3. Key Architecture Changes

#### Embedding Storage
- **UUID Matching**: Qdrant vector IDs match Supabase document UUIDs exactly
- **Separation**: Document content in Supabase, embeddings in Qdrant
- **Retrieval**: Vector search in Qdrant returns UUIDs → Fetch full docs from Supabase

#### Updated Files

**Configuration:**
- `config/settings.py` - Added Qdrant and Gemini settings
- `.env.example` - Updated environment variables

**Database:**
- `src/db/schema.sql` - Removed embedding column and vector extension
- `src/db/models.py` - Removed embedding field from Document model
- `src/db/qdrant_client.py` - NEW: Qdrant client service
- `src/db/__init__.py` - Added Qdrant exports

**Ingestion:**
- `src/ingestion/embeddings.py` - Switched to Gemini embedding API
- `src/ingestion/web_agent.py` - Store embeddings in Qdrant with matching UUID

**Retrieval:**
- `src/retrieval/document_retriever.py` - Query Qdrant then fetch from Supabase
- `src/retrieval/query_router.py` - Use Gemini for LLM-based routing

**Classification:**
- `src/classification/sector_classifier.py` - Use Gemini for classification

**Dependencies:**
- `requirements.txt` - Removed OpenAI/Langchain, added Gemini + Qdrant client

### 4. Environment Variables Required

```bash
# Supabase (for document storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Qdrant (for vector storage)
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key
```

### 5. Data Flow

**Ingestion:**
1. Fetch/parse content
2. Generate embedding using Gemini
3. Insert document into Supabase → Get UUID
4. Store embedding in Qdrant using same UUID

**Retrieval:**
1. Generate query embedding using Gemini
2. Search Qdrant → Get UUIDs + scores
3. Fetch full documents from Supabase using UUIDs
4. Return merged results with similarity scores

### 6. Category Enforcement

**Agent categories** remain limited to their scopes:
- Web agents use only `WebSourceType` values
- Time-series agents use only `TimeSeriesType` values
- **Never** use sector categories in agent type fields
- Sector categories are only for economic domain classification

### 7. Benefits of This Architecture

✅ **Scalability**: Qdrant handles millions of vectors efficiently
✅ **Flexibility**: Can swap embedding models without touching Supabase
✅ **Cost**: Gemini is more cost-effective than OpenAI
✅ **Performance**: Dedicated vector database for fast similarity search
✅ **Simplicity**: UUID matching keeps data synchronized

### 8. Models in Use

- **Chat/Reasoning**: `gemini-2.0-flash-exp`
- **Embeddings**: `models/embedding-001` (768 dimensions)
- **Task Types**: 
  - `retrieval_document` for document embedding
  - `retrieval_query` for query embedding

### 9. Migration Steps for Existing Data

If you have existing data in the old system:

1. Export documents from Supabase
2. Re-generate embeddings using Gemini
3. Upload to Qdrant with matching UUIDs
4. Run schema migration to drop embedding column

### 10. Testing

Test the integration:

```python
from src.ingestion import WebSearchAgent
from src.retrieval import DocumentRetriever

# Ingest
agent = WebSearchAgent()
docs = agent.ingest_text(
    title="Test Document",
    content="This is a test about cement exports",
    source_type="news_article"
)
# Documents stored in Supabase, embeddings in Qdrant

# Retrieve
retriever = DocumentRetriever()
results = retriever.search("cement exports", limit=5)
# Query Qdrant → Get UUIDs → Fetch from Supabase
print(results)
```

## Notes

- Qdrant automatically creates collections on first use
- Gemini has different rate limits than OpenAI - adjust accordingly
- Vector dimension changed from 1536 (OpenAI) to 768 (Gemini)
- All LLM calls now use Gemini's JSON mode for structured outputs
