# 🤖 Fintex Q&A Agents - Quick Guide

## What This Does

Your data is **already being ingested automatically** into:
- **Supabase**: Document content, time-series data
- **Qdrant**: Vector embeddings

**This pipeline provides Q&A agents** that:
1. ✅ Read from your existing data
2. ✅ Answer user questions intelligently
3. ✅ Use Gemini 2.0 Flash for reasoning
4. ✅ Stay within their designated category boundaries

## 🚀 Quick Start

### 1. Install & Configure

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your credentials:
# - SUPABASE_URL, SUPABASE_KEY
# - QDRANT_URL, QDRANT_API_KEY  
# - GEMINI_API_KEY
```

### 2. Ask Questions (CLI)

```bash
# Interactive mode
python qa_agent.py --interactive

# Single question
python qa_agent.py --query "What is the current USD/PKR rate?"

# Brief answer
python qa_agent.py --query "Why did cement exports rise?" --format brief

# Simple mode (faster, no ToT reasoning)
python qa_agent.py --query "Show KSE-100 trend" --simple
```

### 3. Use the API

```bash
# Start API server
python -m uvicorn src.api.main:app --reload --port 8000

# Ask via API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Why did cement exports rise?", "use_reasoning": true}'

# API docs
open http://localhost:8000/docs
```

## 🎯 Agent Capabilities

### Automatic Query Routing
- **Narrative queries** → Searches documents in Qdrant
- **Numeric queries** → Fetches time-series data
- **Hybrid queries** → Uses both sources

### Category-Aware Retrieval
- Detects sector automatically (banking, stocks, commodities, etc.)
- Filters by agent type (news, reports, tick data, etc.)
- **Never mixes** agent categories with sector categories

### Reasoning Modes

**Full Reasoning (Tree of Thought)**:
```python
from src.reasoning import ReasoningEngine, AnswerSynthesizer

engine = ReasoningEngine()
result = engine.reason("Why did cement exports rise last month?")

synthesizer = AnswerSynthesizer()
answer = synthesizer.synthesize(result)
print(answer["answer"])
```

**Simple Retrieval** (faster):
```python
evidence = engine.reason_simple("What is USD/PKR rate?")
answer = synthesizer.synthesize_simple(
    query="What is USD/PKR rate?",
    documents=evidence["document_evidence"],
    timeseries=evidence["timeseries_evidence"]
)
```

## 📊 Example Questions

Try these with your data:

```bash
# Policy questions
python qa_agent.py -q "What was the SBP's recent policy decision?"

# Market questions  
python qa_agent.py -q "Show me KSE-100 trend for last week"

# Economic questions
python qa_agent.py -q "Why is inflation rising?"

# Sector-specific
python qa_agent.py -q "What's happening in the cement sector?"

# Comparative
python qa_agent.py -q "Compare OGDC and PPL stock performance"
```

## 🏗️ How It Works

```
User Query
    ↓
Query Router (Gemini)
    ├─ Detect intent (narrative/numeric/hybrid)
    ├─ Identify sector category
    └─ Extract entities & time range
    ↓
Reasoning Engine
    ├─ Decompose into sub-questions (ToT)
    ├─ Search Qdrant for documents
    ├─ Fetch time-series from Supabase
    └─ Gather evidence
    ↓
Answer Synthesizer (Gemini)
    ├─ Generate coherent answer
    ├─ Include citations
    └─ Assess confidence
    ↓
Return to User
```

## 🎓 Category System

**Agent Categories** describe **how** data was collected:
- Web: `breaking_update`, `deep_dive`, `news_article`, etc.
- Time-series: `tick_stream`, `end_of_day_batch`, etc.

**Sector Categories** describe **what** the data is about:
- `banking`, `bonds`, `commodities`, `stocks`, etc. (11 fixed)

**Rule**: Agents **never** cross boundaries. Each stays in its lane.

## 📁 Key Components

| Component | Purpose |
|-----------|---------|
| `qa_agent.py` | CLI interface for Q&A |
| `src/reasoning/reasoning_engine.py` | Tree of Thought decomposition |
| `src/reasoning/answer_synthesizer.py` | Answer generation |
| `src/retrieval/query_router.py` | Query analysis & routing |
| `src/retrieval/document_retriever.py` | Qdrant → Supabase retrieval |
| `src/retrieval/timeseries_retriever.py` | Time-series queries |
| `src/api/main.py` | FastAPI endpoints |

## 🔧 Configuration

Edit `config/settings.py` or `.env`:

```python
# AI Models
chat_model = "gemini-2.0-flash-exp"
embedding_model = "models/embedding-001"

# Vector Database
qdrant_collection = "documents"

# Chunking (if you need to adjust)
chunk_size = 1000
chunk_overlap = 200
```

## 📚 API Endpoints

```
GET  /health                    # Health check
POST /chat                      # Main Q&A endpoint
POST /chat/route                # Query routing only
POST /search/documents          # Document search
GET  /series/{id}/latest        # Latest time-series value
GET  /series/{id}/trend         # Trend analysis
GET  /dashboard/sectors         # Sector summary
GET  /dashboard/recent          # Recent activity
```

## ⚡ Performance Tips

1. **Use simple mode** for quick factual queries
2. **Use full reasoning** for complex analytical questions
3. **Specify sector** if known (faster retrieval)
4. **Limit results** to reduce latency

## 🆘 Troubleshooting

**"No results found"**:
- Check if data exists in your database
- Verify Qdrant has embeddings
- Try broader search terms

**Slow responses**:
- Use `--simple` mode
- Reduce search limits
- Check Gemini API quota

**Connection errors**:
- Verify `.env` configuration
- Check Supabase/Qdrant URLs
- Ensure API keys are valid

## 📖 More Info

- Full docs: [README.md](README.md)
- Migration guide: [MIGRATION.md](MIGRATION.md)
- API docs: http://localhost:8000/docs (when server running)

---

**Ready to chat?** Run `python qa_agent.py --interactive` 🚀
