# 🤖 Multi-Agent Fintex System - Overview

## System Architecture

This system implements a **4-agent architecture** for Pakistan financial data analysis:

### The 4 Agents

#### 🤖 Agent 1: News & Global Data Agent
- **Implementation**: `WebSearchAgent` (ingestion) + `DocumentRetriever` (retrieval)
- **Retrieves**: Global news, government data, economic indicators
- **Sources**: SBP, SECP, PBS, news articles, policy documents

#### 🤖 Agent 2: Economic Data Agent
- **Implementation**: `TimeSeriesRetriever`
- **Retrieves**: Macroeconomic data, financial indicators, market reports
- **Data**: GDP, CPI, inflation, exchange rates, interest rates

#### 🤖 Agent 3: Real-Time Market Agent
- **Implementation**: `PakistanStockRetriever`
- **Retrieves**: Live stock prices (PSX), market movements, trading data
- **Database**: `stock_prices` table in Supabase

#### 🤖 Agent 4: Analysis & Reasoning Agent
- **Implementation**: `ReasoningEngine` + `AnswerSynthesizer` + `QueryRouter`
- **Functions**: 
  - Coordinates all other agents
  - Performs trend analysis and comparison
  - Provides reasoning and summarization
  - Generates final natural language answers

### Data Flow

```
User Query
    ↓
Agent 4: Query Router (analyzes query)
    ↓
Agent 4: Reasoning Engine (coordinates retrieval)
    ├──→ Agent 1 (documents/news)
    ├──→ Agent 2 (economic data)
    └──→ Agent 3 (stock data)
    ↓
Agent 4: Answer Synthesizer (generates answer)
    ↓
Final Answer with Citations
```

## Quick Start

### Interactive Mode
```bash
python qa_agent.py --interactive
```

### Single Query
```bash
python qa_agent.py --query "What is the latest price of AKBLTFC6?"
```

### API Server
```bash
python -m uvicorn src.api.main:app --reload --port 8000
```

## Key Features

- ✅ **Multi-Agent Collaboration**: All 4 agents work together automatically
- ✅ **Intelligent Routing**: Queries automatically routed to relevant agents
- ✅ **Pakistan Focus**: Specialized for Pakistan Stock Exchange (PSX)
- ✅ **Natural Language**: Ask questions in plain English
- ✅ **Citation Support**: All answers include source references
- ✅ **Confidence Scoring**: Know how reliable the answer is

## Example Queries

- "What is the latest price of AKBLTFC6?"
- "How has AKBLTFC6 performed this month?"
- "What are the top gainers in PSX?"
- "Show me market trends"
- "Why did cement exports rise?"

## Database Schema

### Documents (Agent 1)
- Stored in Supabase + Qdrant (vectors)
- Contains: news, reports, policies

### Time Series (Agent 2)
- Tables: `series_registry`, `timeseries_points`
- Contains: economic indicators, market data

### Stock Prices (Agent 3)
- Table: `stock_prices`
- Contains: OHLC data, volume for PSX stocks

## Documentation

- **README.md** - Complete system documentation
- **QUICKSTART.md** - Getting started guide
- **AGENTS_OVERVIEW.md** - Detailed agent information
- **AGENT3_DOCUMENTATION.md** - Stock market agent details

## Configuration

Edit `.env` file:
```env
SUPABASE_URL=your-url
SUPABASE_KEY=your-key
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-qdrant-key
GEMINI_API_KEY=your-gemini-key
```

## Status

✅ All 4 agents implemented and operational
✅ Multi-agent coordination working
✅ Production ready

## Support

Run examples:
```bash
python examples.py                          # General examples
python examples_agent3_pakistan_stocks.py   # Stock agent examples
```
