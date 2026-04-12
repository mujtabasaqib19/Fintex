"""
Category definitions for the pipeline.
Enforces separation between agent categories and sector categories.
"""
from enum import Enum
from typing import Set


# =============================================================================
# SECTOR CATEGORIES (Economic Domain - Fixed 11 categories)
# =============================================================================
class SectorCategory(str, Enum):
    """
    Fixed 11 economic sector categories.
    These describe the ECONOMIC DOMAIN of the content.
    NEVER use these in source_type or series_type fields.
    """
    BANKING = "banking"
    BONDS = "bonds"
    COMMODITIES = "commodities"
    CORPORATE_ACTIONS = "corporate_actions"
    CURRENCY_FX = "currency_fx"
    DERIVATIVES = "derivatives"
    ECONOMIC_INDICATORS = "economic_indicators"
    FUNDS_ETFS = "funds_etfs"
    INSURANCE = "insurance"
    REAL_ESTATE = "real_estate"
    STOCKS = "stocks"


# =============================================================================
# AGENT CATEGORIES - WEB SEARCH (Data Type/Collection Intent)
# =============================================================================
class WebSourceType(str, Enum):
    """
    Web-search agent source types.
    These describe the TYPE/INTENT of web content collection.
    NEVER use sector categories here.
    """
    BREAKING_UPDATE = "breaking_update"
    DEEP_DIVE = "deep_dive"
    POLICY_DOCUMENT = "policy_document"
    INDUSTRY_REPORT = "industry_report"
    EARNINGS_RELEASE = "earnings_release"
    REGULATORY_FILING = "regulatory_filing"
    NEWS_ARTICLE = "news_article"
    RESEARCH_PAPER = "research_paper"
    MARKET_COMMENTARY = "market_commentary"
    PRESS_RELEASE = "press_release"


# =============================================================================
# AGENT CATEGORIES - TIME SERIES (Data Type/Collection Intent)
# =============================================================================
class TimeSeriesType(str, Enum):
    """
    Time-series agent series types.
    These describe the TYPE/INTENT of time-series data collection.
    NEVER use sector categories here.
    """
    TICK_STREAM = "tick_stream"
    INTERVAL_SNAPSHOT = "interval_snapshot"
    END_OF_DAY_BATCH = "end_of_day_batch"
    INTRADAY_OHLC = "intraday_ohlc"
    DAILY_INDICATOR = "daily_indicator"
    WEEKLY_AGGREGATE = "weekly_aggregate"
    MONTHLY_AGGREGATE = "monthly_aggregate"
    QUARTERLY_REPORT = "quarterly_report"
    ANNUAL_SUMMARY = "annual_summary"
    REAL_TIME_QUOTE = "real_time_quote"


# =============================================================================
# VALIDATION HELPERS
# =============================================================================
def get_sector_categories() -> Set[str]:
    """Get all valid sector category values."""
    return {cat.value for cat in SectorCategory}


def get_web_source_types() -> Set[str]:
    """Get all valid web source type values."""
    return {st.value for st in WebSourceType}


def get_timeseries_types() -> Set[str]:
    """Get all valid time-series type values."""
    return {tt.value for tt in TimeSeriesType}


def validate_sector_category(value: str) -> bool:
    """Validate that a value is a valid sector category."""
    return value in get_sector_categories()


def validate_no_sector_in_agent_type(value: str) -> bool:
    """Ensure agent types don't contain sector categories."""
    sector_values = get_sector_categories()
    return value not in sector_values


def normalize_subcategory(value: str) -> str:
    """
    Normalize subcategory to snake_case.
    Examples:
        "Cement Exports" -> "cement_exports"
        "KSE-100" -> "kse_100"
        "USD/PKR" -> "usd_pkr"
    """
    import re
    # Replace common separators with underscores
    normalized = re.sub(r'[-/\s]+', '_', value.strip())
    # Remove non-alphanumeric except underscores
    normalized = re.sub(r'[^a-zA-Z0-9_]', '', normalized)
    # Convert to lowercase
    normalized = normalized.lower()
    # Remove multiple consecutive underscores
    normalized = re.sub(r'_+', '_', normalized)
    # Strip leading/trailing underscores
    return normalized.strip('_')


# =============================================================================
# SUBCATEGORY EXAMPLES (for reference, not exhaustive)
# =============================================================================
SUBCATEGORY_EXAMPLES = {
    SectorCategory.COMMODITIES: [
        "cement", "clinker_exports", "coal", "cotton", "crude_oil",
        "gold", "silver", "wheat", "rice", "sugar", "brent"
    ],
    SectorCategory.STOCKS: [
        "kse100", "kse30", "kmi30", "ogdc", "ppl", "hub_power",
        "lucky_cement", "engro", "mcb", "ubl"
    ],
    SectorCategory.CURRENCY_FX: [
        "usd_pkr", "eur_pkr", "gbp_pkr", "aed_pkr", "sar_pkr",
        "cny_pkr", "jpy_pkr"
    ],
    SectorCategory.BANKING: [
        "kibor", "sbp_rate", "discount_rate", "interbank_rate",
        "deposit_rates", "lending_rates"
    ],
    SectorCategory.BONDS: [
        "pib_3y", "pib_5y", "pib_10y", "tbills_3m", "tbills_6m",
        "tbills_12m", "sukuk", "ijara"
    ],
    SectorCategory.ECONOMIC_INDICATORS: [
        "cpi", "inflation", "gdp", "trade_balance", "remittances",
        "foreign_reserves", "current_account", "fiscal_deficit"
    ],
}
