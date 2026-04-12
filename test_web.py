import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.reasoning.reasoning_engine import ReasoningEngine
from src.retrieval.live_web_retriever import LiveWebRetriever
from src.retrieval.query_router import QueryRouter

def test():
    router = QueryRouter()
    routing = router.route("What is the latest news about SBP?", use_llm=False)
    print("Routing:", routing)
    
    web = LiveWebRetriever()
    print("Web enabled?", web.enabled)
    if web.enabled:
        docs = web.search_news("SBP", limit=2)
        print("Web docs:", docs)

if __name__ == "__main__":
    test()
