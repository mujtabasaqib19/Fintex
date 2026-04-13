# 🏛️ FINTEX – Comprehensive Architecture & System Handbook

> **A Multi-Agent Intelligent Research Pipeline for the Pakistan Financial Ecosystem.**

Fintex is a state-of-the-art financial research agent designed specifically for the Pakistan Stock Exchange (PSX) and macroeconomic data. It represents a paradigm shift from simple "Generative AI" to **"Grounded Financial Intelligence"**. It ensures that every response is backed by data, verified via semantic search, and visualized through interactive dashboards.

---

## 📸 The Vision
In the world of Finance, "hallucination" is not an option. A wrong price or a misunderstood policy rate can lead to catastrophic investment decisions. Fintex was built to bridge the gap between the speed of Large Language Models (LLMs) and the rigidity of financial databases, creating a "Trusted Analyst" experience.

---

## 🏗️ 1. Multi-Dimensional Architecture

Fintex follows a **"Modular Micro-Kernel"** architecture where the reasoning engine is decoupled from data sources. This allows the system to remain model-agnostic while scaling the data tier.

### 🧩 Core Components
1.  **Strategic Architect (Reasoning):** Powered by **Google Gemini 2.0 Flash**. It handles intent detection, complex summarization, and query routing.
2.  **Financial Specialist (Generation):** Powered by **FinGPT** (via Hugging Face). It specializes in the "Human-Like" but technical tone of an investment banker.
3.  **Semantic Memory (RAG):** Powered by **Qdrant**. Stores 10,000+ chunks of annual reports, brokerage notes, and economic surveys.
4.  **Relational Foundation:** Powered by **Supabase (PostgreSQL)**. Stores real-time OHLCV (Open, High, Low, Close, Volume) data for hundreds of stocks.
5.  **Intelligence Web:** Powered by **SerpAPI**. Fetches real-time "Zero-Day" news from Google News and financial portals.

---

## 🔄 2. The "Life of a Query" (Step-by-Step)

When a user types: *"Is ENGRO a good buy after the latest SBP policy change?"*, the following massive pipeline is triggered:

### Phase A: Intent & Routing
*   **Query Categorization:** The system classifies the query using a hybrid approach (Keywords + Gemini Reasoning). It determines if the query is `stocks`, `theory`, `monetary_policy`, or `macro`.
*   **Symbol Extraction:** Using Regex and NER (Named Entity Recognition), the system identifies `ENGRO` as the primary ticker.

### Phase B: Parallel Data Harvesting
The system launches **3 parallel threads** to gather context:
1.  **Supabase Search:** Fetches the last 30–100 days of price data for `ENGRO`.
2.  **Qdrant Vector Search:** Searches for "ENGRO" and "SBP Policy" inside the indexed PDF knowledge base.
3.  **SerpAPI Fetch:** Scrapes the last 24 hours of news regarding `ENGRO` and the SBP interest rate.

### Phase C: Context Harmonization
The **Strategic Architect (Gemini)** receives the raw chunks from all sources. It filters out noise, resolves contradictions, and creates a "Master Context" document.

### Phase D: The Decision Matrix (XAI)
The system evaluates the quality of the gathered data:
*   **High Confidence (88-96%):** Data found in both Supabase (relational) and Qdrant (verified docs).
*   **Medium Confidence (70-85%):** Data found only in one source or via live web.
*   **Low Confidence (40-65%):** No data found; falling back to pure AI reasoning.

### Phase E: Final Synthesis (Section 7 & 8)
The **FinGPT Specialist** takes the Master Context and formats the answer using strict templates:
- **Stocks:** Background → Performance → Fintex Investment Opinion.
- **Theory:** Definition → Detailed Explanation → Pakistan Context → Further Reading.

### Phase F: UI Rendering
The Frontend (React) receives a JSON packet containing:
- The Markdown answer.
- The Accuracy Score.
- **Chart Data:** A full history of `ENGRO` prices to render a **Recharts** dashboard.
- **Source Badges:** Clickable links to the exact documents used.

---

## 📂 3. Technical Folder Breakdown

```text
/
├── frontend/               # React + Vite (The Glassmorphic Dashboard)
│   ├── src/components/     # Specialized UI components (Dashboards, Accuracy Badges)
│   ├── src/pages/          # Main ChatPage and Analytics views
│   └── src/hooks/          # Custom hooks for API streaming and chart logic
├── src/                    # Backend (The Intelligence Layer)
│   ├── api/                # FastAPI Endpoints (Streaming, History, Tickers)
│   ├── reasoning/          # THE BRAIN: fintex_pipeline.py (Orchestration)
│   ├── retrieval/          # DATA HUNTERS: Logic for searching Qdrant/Supabase/Web
│   ├── ingestion/          # ETL: Converting PDFs and CSVs into Vector Embeddings
│   ├── db/                 # Connectors for Qdrant and Supabase
│   └── classification/     # Fine-grained query routing logic
├── scripts/                # Utility scripts for database migration and bulk embedding
├── config/                 # System-wide settings and environment management
└── Dockerfile              # Containerization for production deployment
```

---

## 🛡️ 4. Explainable AI (XAI) Deep Dive

Fintex implements **"Self-Correcting Transparency"**. 
Most AI tools just give an answer. Fintex tells you **Why** and **How Sure** it is.

*   **Groundedness:** Every claim made in the "Investment Opinion" section is cross-referenced against the `retrieved_chunks`.
*   **Source Verification:** The "Verified Knowledge Base" label only appears if the cosine similarity in Qdrant is > 0.85. 
*   **Hallucination Guard:** If the data is missing, the system is programmed to say *"I don't have enough verified data from the PSX archives for this specific claim."*

---

## 📊 5. Visual Excellence (UI/UX)
The frontend is built to provide a **Premium Analyst Desktop** experience:
- **Glassmorphism:** Elegant dark/light modes with blurred backgrounds.
- **Micro-Animations:** Use of `framer-motion` for smooth layout transitions when charts appear.
- **Interactive Legends:** Hover over any point on the stock chart to see exact price and volume on that date.

---

## ⚙️ 6. How to Run (Technical Setup)

### Prerequisites
- Python 3.9+
- Node.js 18+
- API Keys: Google Gemini, Supabase, Qdrant, SerpAPI, Hugging Face.

### Backend Setup
1. `pip install -r requirements.txt`
2. Configure `.env` with your API credentials.
3. `python src/api/main.py` (Server starts at `http://localhost:8000`)

### Frontend Setup
1. `cd frontend`
2. `npm install`
3. `npm run dev`

---

## 🛸 7. The Roadmap
- [ ] **Agentic Analysis:** Let the AI browse the web interactively for 5 minutes for "Deep Research".
- [ ] **Portfolio Integration:** Allow users to upload their holdings for personalized risk analysis.
- [ ] **Voice Intelligence:** Integration with SBP speech-to-text for live policy briefings.

---
### 🤝 Project Credits
Created with ❤️ for the Pakistan Financial Community.
*"Turning Market Noise into Actionable Intelligence."*
