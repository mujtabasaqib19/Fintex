-- =============================================================================
-- DATABASE SCHEMA FOR DATA ANALYST AGENTS PIPELINE
-- Run this in your Supabase SQL Editor
-- NOTE: Embeddings are stored in Qdrant, not in this database
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. DOCUMENTS TABLE (Web-Search Content)
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Agent category (data type/collection intent)
    -- Values: breaking_update, deep_dive, policy_document, industry_report, etc.
    source_type TEXT NOT NULL,
    
    -- Economic sector category (fixed 11)
    -- Values: banking, bonds, commodities, corporate_actions, currency_fx,
    --         derivatives, economic_indicators, funds_etfs, insurance,
    --         real_estate, stocks
    sector_category TEXT,
    
    -- Dynamic subcategory (normalized snake_case)
    -- Examples: cement, kibor, kse100, usd_pkr
    subcategory TEXT,
    
    -- Content
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT,
    source_filename TEXT,
    
    -- Timestamps
    published_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Additional data
    metadata JSONB DEFAULT '{}',
    
    -- NOTE: Embeddings are stored in Qdrant with matching UUID
    
    -- Constraints
    CONSTRAINT valid_source_type CHECK (
        source_type IN (
            'breaking_update', 'deep_dive', 'policy_document', 'industry_report',
            'earnings_release', 'regulatory_filing', 'news_article', 'research_paper',
            'market_commentary', 'press_release'
        )
    ),
    CONSTRAINT valid_sector_category CHECK (
        sector_category IS NULL OR sector_category IN (
            'banking', 'bonds', 'commodities', 'corporate_actions', 'currency_fx',
            'derivatives', 'economic_indicators', 'funds_etfs', 'insurance',
            'real_estate', 'stocks'
        )
    ),
    -- CRITICAL: source_type can NEVER be a sector category
    CONSTRAINT source_not_sector CHECK (
        source_type NOT IN (
            'banking', 'bonds', 'commodities', 'corporate_actions', 'currency_fx',
            'derivatives', 'economic_indicators', 'funds_etfs', 'insurance',
            'real_estate', 'stocks'
        )
    )
);

-- Indexes for documents
CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_sector_category ON documents(sector_category);
CREATE INDEX IF NOT EXISTS idx_documents_subcategory ON documents(subcategory);
CREATE INDEX IF NOT EXISTS idx_documents_published_at ON documents(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_ingested_at ON documents(ingested_at DESC);


-- =============================================================================
-- 2. SERIES REGISTRY TABLE (Time-Series Metadata)
-- =============================================================================
CREATE TABLE IF NOT EXISTS series_registry (
    series_id TEXT PRIMARY KEY,  -- e.g., psx:ogdc:close:1d
    
    -- Agent category (data type/collection intent)
    series_type TEXT NOT NULL,
    
    -- Provider info
    provider TEXT NOT NULL,
    symbol TEXT NOT NULL,
    metric TEXT NOT NULL,
    frequency TEXT NOT NULL,
    timezone TEXT DEFAULT 'Asia/Karachi',
    
    -- Economic domain (optional)
    sector_category TEXT,
    subcategory TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_series_type CHECK (
        series_type IN (
            'tick_stream', 'interval_snapshot', 'end_of_day_batch', 'intraday_ohlc',
            'daily_indicator', 'weekly_aggregate', 'monthly_aggregate',
            'quarterly_report', 'annual_summary', 'real_time_quote'
        )
    ),
    CONSTRAINT valid_registry_sector_category CHECK (
        sector_category IS NULL OR sector_category IN (
            'banking', 'bonds', 'commodities', 'corporate_actions', 'currency_fx',
            'derivatives', 'economic_indicators', 'funds_etfs', 'insurance',
            'real_estate', 'stocks'
        )
    ),
    -- CRITICAL: series_type can NEVER be a sector category
    CONSTRAINT series_not_sector CHECK (
        series_type NOT IN (
            'banking', 'bonds', 'commodities', 'corporate_actions', 'currency_fx',
            'derivatives', 'economic_indicators', 'funds_etfs', 'insurance',
            'real_estate', 'stocks'
        )
    )
);

-- Indexes for series_registry
CREATE INDEX IF NOT EXISTS idx_registry_series_type ON series_registry(series_type);
CREATE INDEX IF NOT EXISTS idx_registry_provider ON series_registry(provider);
CREATE INDEX IF NOT EXISTS idx_registry_symbol ON series_registry(symbol);
CREATE INDEX IF NOT EXISTS idx_registry_sector ON series_registry(sector_category);


-- =============================================================================
-- 3. TIMESERIES POINTS TABLE (Numeric Data)
-- =============================================================================
CREATE TABLE IF NOT EXISTS timeseries_points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Reference to registry
    series_id TEXT NOT NULL REFERENCES series_registry(series_id),
    
    -- Agent category (denormalized for query performance)
    series_type TEXT NOT NULL,
    
    -- Economic domain (denormalized)
    sector_category TEXT,
    subcategory TEXT,
    
    -- Data point
    timestamp TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT,
    
    -- Source
    provider TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT valid_point_series_type CHECK (
        series_type IN (
            'tick_stream', 'interval_snapshot', 'end_of_day_batch', 'intraday_ohlc',
            'daily_indicator', 'weekly_aggregate', 'monthly_aggregate',
            'quarterly_report', 'annual_summary', 'real_time_quote'
        )
    ),
    CONSTRAINT valid_point_sector_category CHECK (
        sector_category IS NULL OR sector_category IN (
            'banking', 'bonds', 'commodities', 'corporate_actions', 'currency_fx',
            'derivatives', 'economic_indicators', 'funds_etfs', 'insurance',
            'real_estate', 'stocks'
        )
    ),
    CONSTRAINT point_series_not_sector CHECK (
        series_type NOT IN (
            'banking', 'bonds', 'commodities', 'corporate_actions', 'currency_fx',
            'derivatives', 'economic_indicators', 'funds_etfs', 'insurance',
            'real_estate', 'stocks'
        )
    ),
    -- Unique constraint to prevent duplicate data points
    UNIQUE(series_id, timestamp)
);

-- Indexes for timeseries_points
CREATE INDEX IF NOT EXISTS idx_points_series_id ON timeseries_points(series_id);
CREATE INDEX IF NOT EXISTS idx_points_series_type ON timeseries_points(series_type);
CREATE INDEX IF NOT EXISTS idx_points_sector ON timeseries_points(sector_category);
CREATE INDEX IF NOT EXISTS idx_points_timestamp ON timeseries_points(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_points_series_time ON timeseries_points(series_id, timestamp DESC);


-- =============================================================================
-- 4. TIME SERIES AGGREGATION FUNCTIONS
-- =============================================================================

-- Get latest value for a series
CREATE OR REPLACE FUNCTION get_latest_value(target_series_id TEXT)
RETURNS TABLE (
    series_id TEXT,
    timestamp TIMESTAMPTZ,
    value DOUBLE PRECISION,
    unit TEXT
)
LANGUAGE sql
AS $$
    SELECT 
        tp.series_id,
        tp.timestamp,
        tp.value,
        tp.unit
    FROM timeseries_points tp
    WHERE tp.series_id = target_series_id
    ORDER BY tp.timestamp DESC
    LIMIT 1;
$$;


-- Get time series data for a date range
CREATE OR REPLACE FUNCTION get_series_range(
    target_series_id TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    timestamp TIMESTAMPTZ,
    value DOUBLE PRECISION,
    unit TEXT
)
LANGUAGE sql
AS $$
    SELECT 
        tp.timestamp,
        tp.value,
        tp.unit
    FROM timeseries_points tp
    WHERE 
        tp.series_id = target_series_id
        AND tp.timestamp >= start_time
        AND tp.timestamp <= end_time
    ORDER BY tp.timestamp ASC;
$$;


-- Get aggregated stats for a series
CREATE OR REPLACE FUNCTION get_series_stats(
    target_series_id TEXT,
    start_time TIMESTAMPTZ DEFAULT NOW() - INTERVAL '30 days',
    end_time TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    series_id TEXT,
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    avg_value DOUBLE PRECISION,
    latest_value DOUBLE PRECISION,
    point_count BIGINT,
    first_timestamp TIMESTAMPTZ,
    last_timestamp TIMESTAMPTZ
)
LANGUAGE sql
AS $$
    SELECT 
        target_series_id,
        MIN(tp.value),
        MAX(tp.value),
        AVG(tp.value),
        (SELECT value FROM timeseries_points 
         WHERE series_id = target_series_id 
         ORDER BY timestamp DESC LIMIT 1),
        COUNT(*),
        MIN(tp.timestamp),
        MAX(tp.timestamp)
    FROM timeseries_points tp
    WHERE 
        tp.series_id = target_series_id
        AND tp.timestamp >= start_time
        AND tp.timestamp <= end_time;
$$;


-- =============================================================================
-- 6. ROW LEVEL SECURITY (Optional - Enable if needed)
-- =============================================================================
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE series_registry ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE timeseries_points ENABLE ROW LEVEL SECURITY;

-- Example policy (allow all for authenticated users)
-- CREATE POLICY "Allow all for authenticated" ON documents
--     FOR ALL USING (auth.role() = 'authenticated');


-- =============================================================================
-- 6. COMMENTS FOR DOCUMENTATION
-- =============================================================================
COMMENT ON TABLE documents IS 'Web-search content (embeddings stored in Qdrant)';
COMMENT ON TABLE series_registry IS 'Metadata registry for time-series';
COMMENT ON TABLE timeseries_points IS 'Numeric time-series data points';

COMMENT ON COLUMN documents.source_type IS 'Agent category (data collection intent). NEVER a sector category.';
COMMENT ON COLUMN documents.sector_category IS 'Economic domain. One of 11 fixed categories.';
COMMENT ON COLUMN documents.subcategory IS 'Dynamic subcategory in snake_case.';

COMMENT ON COLUMN series_registry.series_type IS 'Agent category (data collection intent). NEVER a sector category.';
COMMENT ON COLUMN timeseries_points.series_type IS 'Agent category. Denormalized from registry for queries.';
