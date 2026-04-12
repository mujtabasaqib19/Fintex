import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retrieval.live_web_retriever import LiveWebRetriever
from src.reasoning.fintex_pipeline import FintexPipeline

def sync_daily_news():
    """
    Fetches latest financial news for key sectors and symbols,
    then vectorizes them into Qdrant semantic memory.
    """
    print(f"[{datetime.now()}] Starting Daily News Vectorization...")
    
    web = LiveWebRetriever()
    pipeline = FintexPipeline()
    
    topics = [
        "Pakistan Stock Exchange breaking news",
        "SBP Monetary Policy updates",
        "Pakistan Fertilizer sector outlook ENGRO FFBL",
        "Pakistan Banking sector news HBL UBL",
        "Pakistan Tech sector analysis SYS TRG"
    ]
    
    for topic in topics:
        print(f"Searching: {topic}...")
        results = web.search_news(topic, limit=5)
        
        for res in results:
            title = res.get('title', '')
            content = res.get('content', '')
            source = res.get('link', 'web_sync')
            
            if len(content) < 100: continue # Skip thin content
            
            # Use pipeline's save logic to sync to Qdrant + Supabase
            pipeline._save_to_qdrant(
                question=f"News about {topic}",
                answer=f"{title}: {content}",
                category="macro", # Internal categorization
                subcategory="daily_sync",
                user_id=None,
                conversation_id=None
            )
            print(f"Vectorized: {title[:50]}...")

    print("News Sync Completed.")

if __name__ == "__main__":
    sync_daily_news()
