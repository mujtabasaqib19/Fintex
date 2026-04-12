"""
Example usage of the Fintex Pipeline.
Demonstrates ingestion, classification, retrieval, and reasoning.
"""
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.categories import (
    SectorCategory, WebSourceType, TimeSeriesType,
    normalize_subcategory
)


def example_category_validation():
    """Demonstrate category separation rules."""
    print("\n" + "="*60)
    print("CATEGORY VALIDATION EXAMPLE")
    print("="*60)
    
    # Show valid categories
    print("\n✅ Valid Web Source Types (Agent Categories):")
    for st in WebSourceType:
        print(f"   - {st.value}")
    
    print("\n✅ Valid Time Series Types (Agent Categories):")
    for tt in TimeSeriesType:
        print(f"   - {tt.value}")
    
    print("\n✅ Valid Sector Categories (Economic Domain):")
    for sc in SectorCategory:
        print(f"   - {sc.value}")
    
    # Subcategory normalization
    print("\n📝 Subcategory Normalization Examples:")
    examples = ["Cement Exports", "KSE-100", "USD/PKR", "  Gold Prices  "]
    for ex in examples:
        print(f"   '{ex}' → '{normalize_subcategory(ex)}'")


def example_document_model():
    """Demonstrate Document model with validation."""
    print("\n" + "="*60)
    print("DOCUMENT MODEL EXAMPLE")
    print("="*60)
    
    from src.db.models import Document
    
    # Valid document
    doc = Document(
        source_type=WebSourceType.NEWS_ARTICLE,  # Agent category
        sector_category=SectorCategory.COMMODITIES,  # Sector category
        subcategory="cement",
        title="Pakistan Cement Exports Surge 15%",
        content="Cement exports from Pakistan rose 15% in Q4 2025...",
        url="https://example.com/cement-news"
    )
    
    print("\n✅ Valid Document Created:")
    print(f"   Source Type: {doc.source_type.value}")
    print(f"   Sector: {doc.sector_category.value}")
    print(f"   Subcategory: {doc.subcategory}")
    print(f"   Title: {doc.title}")
    
    # Try invalid document (would fail)
    print("\n❌ Invalid Example (would raise error):")
    print("   source_type='banking' → ERROR! Sector category in agent field")


def example_timeseries_model():
    """Demonstrate SeriesRegistry and TimeSeriesPoint models."""
    print("\n" + "="*60)
    print("TIME SERIES MODEL EXAMPLE")
    print("="*60)
    
    from src.db.models import SeriesRegistry, TimeSeriesPoint
    
    # Register a series
    registry = SeriesRegistry(
        series_id="psx:kse100:close:1d",
        series_type=TimeSeriesType.END_OF_DAY_BATCH,  # Agent category
        provider="psx",
        symbol="KSE100",
        metric="close",
        frequency="1d",
        sector_category=SectorCategory.STOCKS,  # Sector category
        subcategory="kse100"
    )
    
    print("\n✅ Series Registry Entry:")
    print(f"   Series ID: {registry.series_id}")
    print(f"   Series Type: {registry.series_type.value}")
    print(f"   Sector: {registry.sector_category.value}")
    print(f"   Symbol: {registry.symbol}")
    
    # Create a data point
    point = TimeSeriesPoint(
        series_id="psx:kse100:close:1d",
        series_type=TimeSeriesType.END_OF_DAY_BATCH,
        sector_category=SectorCategory.STOCKS,
        subcategory="kse100",
        timestamp=datetime.now(),
        value=45123.50,
        unit="points",
        provider="psx"
    )
    
    print("\n✅ Data Point Created:")
    print(f"   Timestamp: {point.timestamp}")
    print(f"   Value: {point.value} {point.unit}")


def example_sector_classification():
    """Demonstrate sector classification."""
    print("\n" + "="*60)
    print("SECTOR CLASSIFICATION EXAMPLE")
    print("="*60)
    
    from src.classification import SectorClassifier
    
    classifier = SectorClassifier()
    
    # Test classification
    test_cases = [
        ("SBP Policy Rate Decision", "The State Bank announced a 100bps rate hike..."),
        ("Cement Exports Rise", "Pakistan's cement exports surged 15% due to..."),
        ("KSE-100 Hits Record High", "The benchmark index crossed 50,000 points..."),
        ("USD/PKR Exchange Rate", "The rupee weakened against the dollar...")
    ]
    
    print("\n🔍 Classification Results:")
    for title, content in test_cases:
        sector, subcategory = classifier.classify(title, content, use_llm=False)
        sector_str = sector.value if sector else "None"
        print(f"\n   Title: {title}")
        print(f"   Sector: {sector_str}")
        print(f"   Subcategory: {subcategory}")


def example_query_routing():
    """Demonstrate query routing."""
    print("\n" + "="*60)
    print("QUERY ROUTING EXAMPLE")
    print("="*60)
    
    from src.retrieval import QueryRouter
    
    router = QueryRouter()
    
    queries = [
        "Why did cement exports rise last month?",
        "Show me KSE-100 price trend for the past week",
        "What is the current USD/PKR rate and why is it changing?",
        "Explain the SBP policy rate decision"
    ]
    
    print("\n🔀 Routing Analysis:")
    for query in queries:
        result = router.route(query)
        print(f"\n   Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Needs Docs: {result['needs_documents']}")
        print(f"   Needs TS: {result['needs_timeseries']}")
        print(f"   Sector: {result['sector_category']}")
        print(f"   Entities: {result['entities']}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("DATA ANALYST PIPELINE - EXAMPLES")
    print("="*60)
    
    # Run examples that don't need database
    example_category_validation()
    example_document_model()
    example_timeseries_model()
    
    # These need OpenAI API key
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        if settings.openai_api_key.startswith("sk-"):
            example_sector_classification()
            example_query_routing()
        else:
            print("\n⚠️ Skipping LLM examples (no valid API key)")
    except Exception as e:
        print(f"\n⚠️ Skipping classification/routing examples: {e}")
    
    print("\n" + "="*60)
    print("EXAMPLES COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
