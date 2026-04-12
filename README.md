# Fintex Agents - Full Pipeline

A comprehensive data pipeline for economic/financial data analysis with clear separation between **agent categories** (data collection intent) and **sector categories** (economic domain).

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER QUERY                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QUERY ROUTER (Gemini)                                │
│  • Classify intent (narrative/numeric/hybrid)                                │
│  • Detect sector category                                                    │
│  • Extract time range & entities                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │ DOCUMENTS │   │ TIMESERIES│   │   BOTH    │
            │  (Qdrant) │   │   DATA    │   │  (HYBRID) │
            └───────────┘   └───────────┘   └───────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   REASONING ENGINE (Gemini ToT)                              │
│  • Decompose query into sub-questions                                        │
│  • Gather evidence from documents & time-series                              │
│  • Evaluate confidence                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ANSWER SYNTHESIZER (Gemini)                                │
│  • Generate structured response                                              │
│  • Include citations & numeric evidence                                      │
│  • Provide confidence assessment                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📊 Category Separation (Critical Design)

### 🏷️ Agent Categories (Data Collection Intent)

These describe **how/why** data was collected:

**Web Source Types:**
- `breaking_update` - Urgent news/alerts
- `deep_dive` - In-depth analysis
- `policy_document` - Regulatory/policy docs
- `industry_report` - Sector reports
- `earnings_release` - Financial results
- `regulatory_filing` - Official filings
- `news_article` - General news
- `research_paper` - Academic/research
- `market_commentary` - Expert opinions
- `press_release` - Official statements

**Time Series Types:**
- `tick_stream` - Real-time tick data
- `interval_snapshot` - Periodic snapshots
- `end_of_day_batch` - Daily closing data
- `intraday_ohlc` - Intraday OHLC
- `daily_indicator` - Daily metrics
- `weekly_aggregate` - Weekly summaries
- `monthly_aggregate` - Monthly data
- `quarterly_report` - Quarterly figures
- `annual_summary` - Yearly data
- `real_time_quote` - Live quotes

### 🏦 Sector Categories (Economic Domain)

Fixed 11 categories describing **what** the data is about:

1. `banking` - Banks, KIBOR, SBP rates
2. `bonds` - PIBs, T-bills, sukuk
3. `commodities` - Cement, oil, gold, wheat
4. `corporate_actions` - Dividends, mergers, IPOs
5. `currency_fx` - Forex, USD/PKR, remittances
6. `derivatives` - Futures, options, swaps
7. `economic_indicators` - GDP, CPI, inflation
8. `funds_etfs` - Mutual funds, ETFs, NAV
9. `insurance` - Premiums, claims
10. `real_estate` - Property, construction
11. `stocks` - PSX, KSE-100, equities

### ⚠️ Hard Rules

- **NEVER** store sector categories in `source_type` or `series_type`
- **NEVER** store agent categories in `sector_category`
- `sector_category` must be **exactly** one of the 11 values
- `subcategory` is dynamic but **normalized** (snake_case)

## 📁 Project Structure

```
full-pipeline/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Environment configuration
│   └── categories.py        # Category definitions & validation
├── src/
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py    # Supabase client
│   │   ├── qdrant_client.py # Qdrant vector database client
│   │   ├── models.py        # Pydantic models with validation
│   │   └── schema.sql       # Database schema (documents in Supabase)
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── embeddings.py    # Gemini embeddings
│   │   ├── web_agent.py     # Web content ingestion
│   │   └── timeseries_agent.py  # Time-series ingestion
│   ├── classification/
│   │   ├── __init__.py
│   │   └── sector_classifier.py  # Sector classification (Gemini)
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── query_router.py      # Query analysis (Gemini)
│   │   ├── document_retriever.py # Qdrant → Supabase retrieval
│   │   └── timeseries_retriever.py # Time-series queries
│   ├── reasoning/
│   │   ├── __init__.py
│   │   ├── reasoning_engine.py  # Tree of Thought (Gemini)
│   │   └── answer_synthesizer.py # Response generation (Gemini)
│   └── api/
│       ├── __init__.py
│       └── main.py          # FastAPI endpoints
├── .env.example
├── requirements.txt
├── MIGRATION.md
└── README.md
```

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Supabase anon key
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `QDRANT_URL` - Qdrant cluster URL
- `QDRANT_API_KEY` - Qdrant API key
- `GEMINI_API_KEY` - Google Gemini API key

### 3. Initialize Database

Run the SQL schema in your Supabase SQL Editor:

```bash
# Copy contents of src/db/schema.sql to Supabase SQL Editor
```

### 4. Start the API Server

```bash
cd full-pipeline
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

API documentation available at: `http://localhost:8000/docs`

## 📚 API Endpoints

### Ingestion
- `POST /ingest/url` - Ingest content from URL
- `POST /ingest/text` - Ingest raw text
- `POST /series/register` - Register time series
- `POST /series/point` - Add data point
- `POST /series/points` - Batch add points

### Retrieval
- `POST /search/documents` - Vector similarity search
- `GET /series/{id}/latest` - Get latest value
- `GET /series/{id}/range` - Get date range data
- `GET /series/{id}/trend` - Get trend analysis
- `GET /sector/{sector}/summary` - Sector overview

### Chat
- `POST /chat` - Main Q&A endpoint
- `POST /chat/route` - Query routing analysis

### Dashboard
- `GET /dashboard/sectors` - All sectors with counts
- `GET /dashboard/recent` - Recent activity

## 💡 Usage Examples

### Ingest a News Article

```python
from src.ingestion import WebSearchAgent
from config.categories import WebSourceType, SectorCategory

agent = WebSearchAgent()
docs = agent.ingest_url(
    url="https://example.com/cement-exports-rise",
    source_type=WebSourceType.NEWS_ARTICLE,  # Agent category
    sector_category=SectorCategory.COMMODITIES,  # Sector category
    subcategory="cement"
)
```

### Register and Ingest Time Series

```python
from src.ingestion import TimeSeriesAgent
from config.categories import TimeSeriesType, SectorCategory
from datetime import datetime

agent = TimeSeriesAgent()

# Register series
registry = agent.register_series(
    provider="psx",
    symbol="KSE100",
    metric="close",
    frequency="1d",
    series_type=TimeSeriesType.END_OF_DAY_BATCH,  # Agent category
    sector_category=SectorCategory.STOCKS,  # Sector category
    subcategory="kse100"
)

# Ingest data point
agent.ingest_point(
    series_id="psx:kse100:close:1d",
    timestamp=datetime.now(),
    value=45123.50,
    unit="points"
)
```

### Ask a Question

```python
from src.reasoning import ReasoningEngine, AnswerSynthesizer

engine = ReasoningEngine()
result = engine.reason("Why did cement exports rise last month?")

synthesizer = AnswerSynthesizer()
answer = synthesizer.synthesize(result)

print(answer["answer"])
print("Confidence:", answer["confidence"]["level"])
```

### Search Documents

```python
from src.retrieval import DocumentRetriever
from config.categories import SectorCategory

retriever = DocumentRetriever()
results = retriever.search(
    query="SBP policy rate decision",
    sector_category=SectorCategory.BANKING,
    limit=5
)
```

## 🔒 Data Validation

All models enforce category separation via Pydantic validators:

```python
from src.db.models import Document
from config.categories import WebSourceType, SectorCategory

# ✅ Correct usage
doc = Document(
    source_type=WebSourceType.NEWS_ARTICLE,  # Agent category
    sector_category=SectorCategory.BANKING,  # Sector category
    title="SBP Announces Policy Rate",
    content="..."
)

# ❌ This would raise ValidationError
doc = Document(
    source_type="banking",  # ERROR: Sector category in source_type!
    ...
)
```

## 📊 Database Schema

See `src/db/schema.sql` for full schema with:
- CHECK constraints preventing category mixing
- Vector similarity search function (`match_documents`)
- Time-series aggregation functions
- Proper indexing for performance

## 🤝 Contributing

1. Ensure all categories are properly separated
2. Use type hints throughout
3. Add tests for new functionality
4. Follow existing naming conventions

## 📝 License

MIT License
