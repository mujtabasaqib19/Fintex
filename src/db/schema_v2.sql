-- =============================================================================
-- FINTEX SCHEMA v2.0
-- Deep Fundamental Data Tier & Agentic Actions
-- Includes: Fundamentals, Price Alerts, and Reporting metadata
-- =============================================================================

-- =============================================================================
-- 1. COMPANY FUNDAMENTALS TABLE
-- Stores fiscal performance metrics and valuation ratios
-- =============================================================================
CREATE TABLE IF NOT EXISTS company_fundamentals (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    revenue NUMERIC(20, 2),
    net_profit NUMERIC(20, 2),
    eps NUMERIC(10, 2),
    pe_ratio NUMERIC(10, 2),
    dividend_yield NUMERIC(10, 2),
    market_cap NUMERIC(20, 2),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, fiscal_year)
);

CREATE INDEX IF NOT EXISTS idx_fundamentals_symbol ON company_fundamentals(symbol);
CREATE INDEX IF NOT EXISTS idx_fundamentals_year ON company_fundamentals(fiscal_year);

COMMENT ON TABLE company_fundamentals IS 'Annual financial performance metrics and valuation ratios for PSX companies';

-- =============================================================================
-- 2. PRICE ALERTS TABLE
-- Stores user-defined price notification triggers
-- =============================================================================
CREATE TABLE IF NOT EXISTS price_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    target_price NUMERIC(10, 2) NOT NULL,
    condition TEXT CHECK (condition IN ('above', 'below')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    triggered_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_price_alerts_user ON price_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_price_alerts_symbol ON price_alerts(symbol);
CREATE INDEX IF NOT EXISTS idx_price_alerts_active ON price_alerts(is_active);

COMMENT ON TABLE price_alerts IS 'User price alerts for background tracking and notifications';

-- =============================================================================
-- 3. REPORTING LOG TABLE
-- Tracks generated PDF reports and analytical exports
-- =============================================================================
CREATE TABLE IF NOT EXISTS analytical_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),
    symbol TEXT NOT NULL,
    report_type TEXT DEFAULT 'pdf_analysis',
    file_path TEXT, -- If stored in Supabase Storage
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_user ON analytical_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_symbol ON analytical_reports(symbol);

-- =============================================================================
-- 4. RLS POLICIES
-- =============================================================================
ALTER TABLE company_fundamentals ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytical_reports ENABLE ROW LEVEL SECURITY;

-- Public read for fundamentals
CREATE POLICY "Public read fundamentals" ON company_fundamentals
    FOR SELECT USING (true);

-- Users see their own alerts
CREATE POLICY "Users access own alerts" ON price_alerts
    FOR ALL USING (true);

-- Users see their own reports
CREATE POLICY "Users access own reports" ON analytical_reports
    FOR ALL USING (true);
