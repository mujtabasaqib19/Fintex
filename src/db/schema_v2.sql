-- =============================================================================
-- FINTEX SCHEMA V2 — PERSONALIZATION & FUNDAMENTALS
-- =============================================================================

-- 1. USER PORTFOLIOS
-- Tracks what stocks the user owns for the "Personal Advisor" feature.
CREATE TABLE IF NOT EXISTS public.portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL, -- e.g. ENGRO, FFBL
    quantity NUMERIC DEFAULT 0,
    avg_purchase_price NUMERIC DEFAULT 0,
    total_investment NUMERIC GENERATED ALWAYS AS (quantity * avg_purchase_price) STORED,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, symbol)
);

-- 2. COMPANY FUNDAMENTALS (PSX Specific)
-- Stores 3nd-year financial health snapshots.
-- Note: Reference constraint on symbol removed because stock_prices(symbol) is not unique.
CREATE TABLE IF NOT EXISTS public.company_fundamentals (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL, 
    fiscal_year INT NOT NULL,
    eps NUMERIC,             -- Earnings Per Share
    pe_ratio NUMERIC,        -- Price to Earnings
    div_yield NUMERIC,       -- Dividend Yield %
    revenue_bn NUMERIC,      -- Revenue in Billion PKR
    profit_bn NUMERIC,       -- Net Profit in Billion PKR
    debt_equity_ratio NUMERIC,
    last_updated TIMESTAMPTZ DEFAULT now(),
    UNIQUE(symbol, fiscal_year)
);

-- 3. USER PRICE ALERTS
-- Allows agent to monitor price drops/spikes.
CREATE TABLE IF NOT EXISTS public.price_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    target_price NUMERIC NOT NULL,
    condition TEXT CHECK (condition IN ('above', 'below')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    triggered_at TIMESTAMPTZ
);

-- 4. NEWS CRAWLER LOGS
-- Tracks ingestion health for the autonomous news worker.
CREATE TABLE IF NOT EXISTS public.ingestion_logs (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL, -- e.g. 'SBP Press Release', 'PSX News'
    url TEXT UNIQUE,
    status TEXT,
    items_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS (simplified for now - same as messages)
ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own portfolio" ON public.portfolios
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own alerts" ON public.price_alerts
    USING (auth.uid() = user_id);
