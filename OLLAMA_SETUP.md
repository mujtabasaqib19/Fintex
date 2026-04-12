# ✅ Q&A Agent - Now Using Ollama Embeddings!

## 🎯 What Changed

Your Q&A agent now uses **Ollama** for embeddings instead of Gemini:

### Architecture

```
Embeddings: Ollama (nomic-embed-text) → 768 dimensions
   ↓
Qdrant: Vector storage with 768-dim vectors
   ↓
Retrieval: Match query embeddings to document embeddings
   ↓
Chat: Gemini 2.5 Flash for reasoning and answers
```

## 🔧 Configuration

**Embeddings** (Local via Ollama):
- Model: `nomic-embed-text`
- Dimensions: 768
- Endpoint: `http://localhost:11434`

**Chat/Reasoning** (Cloud via Gemini):
- Model: `gemini-2.5-flash`
- Used for: Query routing, reasoning, answer generation

**Vector Database** (Qdrant):
- Collection: `documents`
- Dimensions: 768 (matches nomic-embed-text)

## 📋 Prerequisites

### 1. Ollama Must Be Running

```bash
# Terminal 1: Start Ollama server
ollama serve

# Terminal 2: Pull embedding model (one-time)
ollama pull nomic-embed-text
```

### 2. Environment Variables

Your `.env` should have:
```bash
# Supabase (for document storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-key
SUPABASE_SERVICE_KEY=your-service-key

# Qdrant (for vectors)
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-key

# Ollama (for embeddings) - Local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Gemini (for chat/reasoning)
GEMINI_API_KEY=your-gemini-key
```

## 🚀 How toUse

### Start the Agent

```bash
python qa_agent.py --interactive
```

### Ask Questions

```
❓ You: What was the impact of tax receipts on the economy in Q2 and Q3 of FY05?
```

The agent will:
1. **Generate query embedding** using Ollama (`nomic-embed-text`)
2. **Search Qdrant** for similar documents (vector similarity)
3. **Fetch documents** from Supabase using matching UUIDs
4. **Reason about evidence** using Gemini 2.5 Flash
5. **Synthesize answer** with citations

## 🔍 How It Works

### Embedding Generation (Ollama)

```python
from src.ingestion.embeddings import EmbeddingService

service = EmbeddingService()

# Query embedding
query_emb = service.embed_query("tax receipts FY05")
# Returns: [0.016, -0.007, 0.013, ...] (768 values)

# Document embedding
doc_emb = service.embed_document("Title", "Content...")
# Returns: [0.012, -0.005, 0.011, ...] (768 values)
```

### Retrieval Flow

```
User Query
    ↓
Ollama Embedding (768-dim vector)
    ↓
Qdrant Search (cosine similarity)
    ↓
Get matching UUIDs + scores
    ↓
Fetch full documents from Supabase
    ↓
Return results with similarity scores
```

### Reasoning Flow

```
Query + Retrieved Documents
    ↓
Gemini: Decompose into sub-questions
    ↓
Gather evidence for each sub-question
    ↓
Gemini: Synthesize coherent answer
    ↓
Return answer with citations + confidence
```

## ✅ Key Features

1. **Local Embeddings**: No API costs, faster, private
2. **Cloud Reasoning**: Powerful Gemini for analysis
3. **UUID Matching**: Qdrant vector IDs = Supabase document IDs
4. **Category Enforcement**: Agents stay in their lanes
5. **Multi-Source**: Combines documents + time-series data

## 📊 Vector Dimensions

| Component | Model | Dimensions |
|-----------|-------|------------|
| Embeddings | nomic-embed-text (Ollama) | 768 |
| Qdrant Collection | documents | 768 |
| Chat | gemini-2.5-flash | N/A |

## ⚠️ Important Notes

1. **Ollama must be running** before starting the agent
2. **Same embedding model** must be used for ingestion and retrieval
3. If you re-ingest data, use the same `nomic-embed-text` model
4. Qdrant collection dimensions=768 matches `nomic-embed-text`

## 🐛 Troubleshooting

**Error: Connection refused (localhost:11434)**
- Start Ollama: `ollama serve`

**Error: Vector dimension mismatch**
- Ensure Qdrant collection has 768 dimensions
- Ensure you're using `nomic-embed-text` for both ingest and retrieve

**Error: Model not found**
- Pull the model: `ollama pull nomic-embed-text`

**No results found**
- Check if data exists in Supabase + Qdrant
- Verify embeddings were generated during ingestion

## 📖 Files Modified

- `src/ingestion/embeddings.py` - Now uses Ollama API
- `config/settings.py` - Added Ollama configuration
- `src/db/qdrant_client.py` - Set to 768 dimensions
- `.env.example` - Added Ollama settings

## 🎉 You're Ready!

The agent is now running and ready to answer questions using:
- ✅ **Ollama** for embeddings (local, free)
- ✅ **Qdrant** for vector search
- ✅ **Supabase** for document storage
- ✅ **Gemini** for intelligent reasoning

Just type your question at the `❓ You:` prompt!
